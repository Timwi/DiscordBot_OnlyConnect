import io
import os.path
import random
import time
import asyncio
import uuid
import math

import discord
from discord.ext import commands
import config
from game import Game
from discord import app_commands
from PIL import Image, ImageOps, ImageDraw, ImageFont


class Bot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        self.tree.copy_global_to(guild=discord.Object(id=config.guild_id))
        await self.tree.sync(guild=discord.Object(id=config.guild_id))


client = Bot()
game = None
greek_letters = 'αβγδεζ'


@client.event
async def on_ready():
    print(f'logged in as {client.user}')


@client.tree.command(name='flip', description='flip a coin')
async def flip(interaction: discord.Interaction):
    result = random.choice(['heads', 'tails'])
    await interaction.response.send_message(result)


@client.tree.command(name='init', description='Initialise a new game')
async def init(interaction: discord.Interaction,
               team_1_name: str, team_1_player_1: discord.Member,
               team_1_player_2: discord.Member, team_1_player_3: discord.Member,
               team_2_name: str, team_2_player_1: discord.Member,
               team_2_player_2: discord.Member, team_2_player_3: discord.Member):
    global game
    if interaction.user.id not in config.admins:
        await interaction.response.send_message('no permission', ephemeral=True)
        return
    game = Game()
    game.team_1_name = team_1_name
    game.team_1_players = {team_1_player_1, team_1_player_2, team_1_player_3}
    game.team_2_name = team_2_name
    game.team_2_players = {team_2_player_1, team_2_player_2, team_2_player_3}
    game.channel = interaction.channel
    team_1_mentions = ', '.join(player.mention for player in game.team_1_players)
    team_2_mentions = ', '.join(player.mention for player in game.team_2_players)
    await interaction.response.send_message(f'**Initialised game**\nTeam {game.team_1_name}: {team_1_mentions}\n'
                                            f'Team {game.team_2_name}: {team_2_mentions}')


@client.tree.command(name='play', description='Initialise a new game')
@app_commands.choices(
    team=[app_commands.Choice(name='1', value=1), app_commands.Choice(name='2', value=2)],
    game_type=[
        app_commands.Choice(name='connection', value='connection'),
        app_commands.Choice(name='sequence', value='sequence'),
        app_commands.Choice(name='grid', value='grid'),
        app_commands.Choice(name='grid_finals', value='grid_finals'),
        app_commands.Choice(name='missing_vowels', value='missing_vowels')
    ]
)
async def play(interaction: discord.Interaction, team: int, game_type: str):
    if interaction.user.id not in config.admins:
        await interaction.response.send_message('no permission', ephemeral=True)
        return
    if game is None:
        await interaction.response.send_message(f'set teams with /init first', ephemeral=True)
        return
    team_name = game.team_1_name if team == 1 else game.team_2_name
    await interaction.response.send_message(f'starting {game_type} for team {team_name}', ephemeral=True)
    if game_type == 'missing_vowels':
        try:
            await play_missing_vowels(game.team_1_players | game.team_2_players)
        except TypeError:
            await interaction.response.send_message(f'failed to find unused tasks for missing_vowels')
        return
    await select_greek_letter(team, game_type)


async def select_greek_letter(team, game_type):
    disabled_tasks = game.disabled_tasks(game_type)
    parent_view = discord.ui.View(timeout=None)
    n_options = 6 if game_type not in ('grid', 'grid_finals') else 2
    btn_ids = []
    for i in range(n_options):
        btn_id = str(uuid.uuid4())
        btn = discord.ui.Button(
            label=greek_letters[i], custom_id=btn_id, disabled=disabled_tasks[i],
            row=(i // 3), style=discord.ButtonStyle.primary)
        btn_ids.append(btn_id)
        parent_view.add_item(btn)
    team_name = game.team_1_name if team == 1 else game.team_2_name
    players = game.team_1_players if team == 1 else game.team_2_players
    other_players = game.team_2_players if team == 1 else game.team_1_players
    mentions = ', '.join(player.mention for player in players)
    msg = await game.channel.send(f'{mentions}\n{team_name}, select a greek letter to play {game_type}', view=parent_view)
    ids = {player.id for player in players}
    btn_click: discord.Interaction = await client.wait_for('interaction', check=lambda e: e.data.get('custom_id') in btn_ids and e.user.id in ids, timeout=None)
    await btn_click.response.defer()
    selection = btn_ids.index(btn_click.data['custom_id'])
    await msg.edit(content=f'{team_name} selected {greek_letters[selection]}, starting {game_type}...', view=None)
    game_functions = {
        'connection': play_connection_or_sequence,
        'sequence': play_connection_or_sequence,
        'grid': play_grid,
        'grid_finals': play_grid
    }
    await game_functions[game_type](team_name, players, other_players, selection, game_type)


def gen_thumbs(images, cols, out_file, s=(250, 250)):
    bw = 2
    pad = 5
    title = 28
    rows = math.ceil(len(images) / cols)
    res = Image.new('RGB', (cols * s[0] + 2 * pad, rows * s[1]), (47, 49, 54))
    for i, image in enumerate(images):
        im = Image.open(os.path.join('tasks', 'images', image))
        im.thumbnail((s[0] - 2 * bw - 2 * pad, s[1] - 2 * bw - 2 * pad - title))
        th = ImageOps.expand(im, border=bw, fill='lightgray')
        x_off = (s[0] - th.width) // 2
        x = (i % cols) * s[0] + pad + x_off
        y = (i // cols) * (s[1]) + pad
        res.paste(th, (x, y + title))
        draw = ImageDraw.Draw(res)
        font = ImageFont.truetype(r'res/DejaVuSans.ttf', 24)
        text = f'{i + 1}'
        w, h = draw.textsize(text, font=font)
        draw.text((x + (th.width - w) // 2, y), text, font=font, fill='lightgray')
    out_file.seek(0)
    res.save(out_file, 'PNG')
    out_file.seek(0)


async def play_connection_or_sequence(team_name, players, other_players, selection, game_type):
    mentions = ', '.join(player.mention for player in players)
    task = game.use_task(game_type, selection)
    images = []
    image_file = io.BytesIO()
    for i in range(len(task)):
        if task[i].startswith('image:'):
            images.append(task[i][6:])
            task[i] = f'image {i + 1}'
    for other_player in other_players:
        try:
            await other_player.edit(deafen=True)
        except discord.HTTPException:
            pass
    embed = discord.Embed(title=f'{game_type} ({team_name})', description='60 seconds remaining', colour=0x5865f2)
    embed.add_field(name='5 Points', value=task[0], inline=False)
    t_start = time.time()
    remaining_time = 60
    buzz_event = asyncio.Event()
    buzzer_id = str(uuid.uuid4())

    class ConnectionListener(discord.ui.View):
        def __init__(self, target_users):
            super().__init__(timeout=None)
            self.target_users = target_users
            self.hints = 1
            self.game_ended = False

        @discord.ui.button(emoji='🔔', custom_id=buzzer_id, style=discord.ButtonStyle.red)
        async def on_buzz(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user not in self.target_users:
                await interaction.response.send_message('😠', ephemeral=True)
                return
            if not self.game_ended:
                self.game_ended = True
                await msg.reply(f'{mentions}\n{team_name} buzzed')
                buzz_event.set()
            await interaction.response.defer()
            for other_player_2 in other_players:
                try:
                    await other_player_2.edit(deafen=False)
                except discord.HTTPException:
                    pass

        @discord.ui.button(label='next')
        async def on_next(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user not in self.target_users:
                await interaction.response.send_message('😠', ephemeral=True)
                return
            hint_limit = 4 if game_type == 'connection' else 3
            if not self.game_ended and self.hints < hint_limit:
                points = 4 - self.hints
                msg.embeds[0].add_field(name=f'{points} Point{"s" if points > 1 else ""}', value=task[self.hints], inline=False)
                if images:
                    gen_thumbs(images[:self.hints + 1], len(images), image_file)
                    file = discord.File(image_file, filename=f'clues{self.hints}.png')
                    msg.embeds[0].set_image(url=f'attachment://clues{self.hints}.png')
                    await msg.edit(embed=msg.embeds[0], attachments=[file])
                else:
                    await msg.edit(embed=msg.embeds[0])
                self.hints += 1
            await interaction.response.defer()

    listener = ConnectionListener(target_users=players)
    if images:
        gen_thumbs(images[:1], len(images), image_file)
        embed.set_image(url=f'attachment://clues.png')
        file = discord.File(image_file, filename='clues.png')
        msg = await game.channel.send(mentions, embed=embed, view=listener, file=file)
    else:
        msg = await game.channel.send(mentions, embed=embed, view=listener)
    while not listener.game_ended and remaining_time > 0:
        remaining_time -= 10
        t_delay = t_start + config.t_connection - time.time() - remaining_time
        try:
            await asyncio.wait_for(buzz_event.wait(), timeout=t_delay)
        except asyncio.exceptions.TimeoutError:
            msg.embeds[0].description = f'{remaining_time} seconds remaining'
            await msg.edit(embed=msg.embeds[0])
    if not listener.game_ended:
        listener.game_ended = True
        await msg.reply(f'{team_name} did not buzz in time')
        for other_player in other_players:
            try:
                await other_player.edit(deafen=False)
            except discord.HTTPException:
                pass
    # reveal remaining prompts
    listener.stop()
    btn_click: discord.Interaction = await client.wait_for('interaction', check=lambda e: e.data.get('custom_id') == buzzer_id and e.user.id in config.admins, timeout=None)
    await btn_click.response.defer()
    hint_limit = 4 if game_type == 'connection' else 3
    if listener.hints < hint_limit:
        while listener.hints < hint_limit:
            points = 4 - listener.hints
            msg.embeds[0].add_field(name=f'{points} Point{"s" if points > 1 else ""}', value=task[listener.hints], inline=False)
            listener.hints += 1
        if images:
            gen_thumbs(images[:hint_limit], len(images), image_file)
            file = discord.File(image_file, filename=f'clues{listener.hints}.png')
            msg.embeds[0].set_image(url=f'attachment://clues{listener.hints}.png')
            await msg.edit(embed=msg.embeds[0], attachments=[file])
        else:
            await msg.edit(embed=msg.embeds[0])
    # reveal solution
    btn_click: discord.Interaction = await client.wait_for('interaction', check=lambda e: e.data.get('custom_id') == buzzer_id and e.user.id in config.admins, timeout=None)
    await btn_click.response.defer()
    if hint_limit == 3:
        msg.embeds[0].add_field(name=f'Solution', value=task[3], inline=False)
    msg.embeds[0].add_field(name=f'Connection', value=task[4], inline=False)
    if images:
        gen_thumbs(images[:hint_limit + 1], len(images), image_file)
        file = discord.File(image_file, filename=f'clues{hint_limit}.png')
        msg.embeds[0].set_image(url=f'attachment://clues{hint_limit}.png')
        await msg.edit(embed=msg.embeds[0], attachments=[file], view=None)
    else:
        await msg.edit(embed=msg.embeds[0], view=None)


async def play_grid(team_name, players, other_players, selection, game_type):
    task = game.use_task(game_type, selection)
    for admin_id in config.admins:
        user = client.get_user(admin_id) or await client.fetch_user(admin_id)
        if not user:
            continue
        dm_channel = user.dm_channel or await user.create_dm()
        if not dm_channel:
            continue
        try:
            await dm_channel.send(f'Grid for {team_name}: <{task[0]}>')
        except discord.HTTPException:
            pass


async def play_missing_vowels(players):
    mentions = ', '.join(player.mention for player in players)
    ids = {player.id for player in players}
    for round_number in range(4):
        task = game.use_task('missing_vowels', round_number)
        parent_view = discord.ui.View(timeout=None)
        buzzer_id = str(uuid.uuid4())
        parent_view.add_item(discord.ui.Button(emoji='🔔', custom_id=buzzer_id, style=discord.ButtonStyle.red))
        embed = discord.Embed(title=f'missing vowels', description=task[0], colour=0x5865f2)
        msg = await game.channel.send(mentions, embed=embed, components=components)
        buzz_msg = None
        for word_number in range(5):
            btn_click: discord.Interaction = await client.wait_for('interaction', check=lambda e: e.data.get('custom_id') == buzzer_id and e.user.id in config.admins, timeout=None)
            await btn_click.response.defer()
            if buzz_msg:
                await buzz_msg.delete()
            if word_number > 0:
                embed = discord.Embed(title=msg.embeds[0].title, description=msg.embeds[0].description)
                for field in msg.embeds[0].fields[:-1]:
                    embed.add_field(name=field.name, value=field.value, inline=False)
                embed.add_field(name=task[-1 + word_number * 2], value=task[word_number * 2], inline=False)
                await msg.edit(embed=embed)
                await asyncio.sleep(5)
            if word_number == 4:
                break
            msg.embeds[0].add_field(name=task[1 + word_number * 2], value='\u200b', inline=False)
            await msg.edit(embed=msg.embeds[0])
            try:
                btn_click: discord.Interaction = await client.wait_for('interaction', check=lambda e: e.data.get('custom_id') == buzzer_id and e.user.id in ids, timeout=10)
                await btn_click.response.defer()
                if btn_click.user in game.team_1_players:
                    team_name = game.team_1_name
                    team_mentions = ', '.join(player.mention for player in game.team_1_players)
                elif btn_click.user in game.team_2_players:
                    team_name = game.team_2_name
                    team_mentions = ', '.join(player.mention for player in game.team_2_players)
                else:
                    team_name = team_mentions = '???'
                buzz_msg = await msg.reply(f'{team_mentions}\n{team_name} buzzed')
            except asyncio.exceptions.TimeoutError:
                buzz_msg = await msg.reply(f'nobody buzzed in time')


if __name__ == '__main__':
    client.run(config.bot_token)
