import time
import asyncio
import discord
from discord.ext import commands
import discord_ui
import config
from game import Game


client = commands.Bot(" ")
slash_options = {'delete_unused': True}
ui = discord_ui.UI(client, slash_options=slash_options)
init_options = [
    discord_ui.SlashOption(str, f'team_1_name', required=True),
    discord_ui.SlashOption(discord_ui.OptionType.MEMBER, f'team_1_player_1', required=True),
    discord_ui.SlashOption(discord_ui.OptionType.MEMBER, f'team_1_player_2', required=True),
    discord_ui.SlashOption(discord_ui.OptionType.MEMBER, f'team_1_player_3', required=True),
    discord_ui.SlashOption(str, f'team_2_name', required=True),
    discord_ui.SlashOption(discord_ui.OptionType.MEMBER, f'team_2_player_1', required=True),
    discord_ui.SlashOption(discord_ui.OptionType.MEMBER, f'team_2_player_2', required=True),
    discord_ui.SlashOption(discord_ui.OptionType.MEMBER, f'team_2_player_3', required=True),
]
play_options = [
    discord_ui.SlashOption(int, 'team', choices=[('1', 1), ('2', 2)], required=True),
    discord_ui.SlashOption(str, 'game_type', choices=[
        ('connection', 'connection'), ('sequence', 'sequence'), ('grid', 'grid'), ('consonants', 'consonants')
    ], required=True),
]
admin_permissions = {
    config.guild_id: discord_ui.SlashPermission(allowed={uid: discord_ui.SlashPermission.USER for uid in config.admins})
}
game = None
greek_letters = 'αβγδεζ'


@client.event
async def on_ready():
    print(f'logged in as {client.user}')


@ui.slash.command('init', options=init_options, default_permission=False, guild_permissions=admin_permissions, guild_ids=[config.guild_id])
async def init(ctx, team_1_name, team_1_player_1, team_1_player_2, team_1_player_3,
               team_2_name, team_2_player_1, team_2_player_2, team_2_player_3):
    global game
    if ctx.author.id not in config.admins:
        await ctx.respond('no permission', hidden=True)
        return
    game = Game()
    game.team_1_name = team_1_name
    game.team_1_players = {team_1_player_1, team_1_player_2, team_1_player_3}
    game.team_2_name = team_2_name
    game.team_2_players = {team_2_player_1, team_2_player_2, team_2_player_3}
    game.channel = ctx.channel
    team_1_mentions = ', '.join(player.mention for player in game.team_1_players)
    team_2_mentions = ', '.join(player.mention for player in game.team_2_players)
    await ctx.respond(f'**Initialised game**\nTeam {game.team_1_name}: {team_1_mentions}\nTeam {game.team_2_name}: {team_2_mentions}')


@ui.slash.command('play', options=play_options, default_permission=False, guild_permissions=admin_permissions, guild_ids=[config.guild_id])
async def play(ctx, team, game_type):
    if ctx.author.id not in config.admins:
        await ctx.respond('no permission', hidden=True)
        return
    if game is None:
        await ctx.respond(f'set teams with /init first', hidden=True)
        return
    team_name = game.team_1_name if team == 1 else game.team_2_name
    await ctx.respond(f'starting {game_type} for team {team_name}', hidden=True)
    if game_type == 'consonants':
        await play_consonants(game.team_1_players | game.team_2_players)
        return
    await select_greek_letter(team, game_type)


async def select_greek_letter(team, game_type):
    disabled_tasks = game.disabled_tasks(game_type)
    if game_type == 'grid':
        components = [
            discord_ui.Button(greek_letters[0], custom_id='0', disabled=disabled_tasks[0]),
            discord_ui.Button(greek_letters[1], custom_id='1', disabled=disabled_tasks[1])
        ]
    else:
        components = [
            discord_ui.ActionRow([
                discord_ui.Button(greek_letters[0], custom_id='0', disabled=disabled_tasks[0]),
                discord_ui.Button(greek_letters[1], custom_id='1', disabled=disabled_tasks[1]),
                discord_ui.Button(greek_letters[2], custom_id='2', disabled=disabled_tasks[2])
            ]),
            discord_ui.ActionRow([
                discord_ui.Button(greek_letters[3], custom_id='3', disabled=disabled_tasks[3]),
                discord_ui.Button(greek_letters[4], custom_id='4', disabled=disabled_tasks[4]),
                discord_ui.Button(greek_letters[5], custom_id='5', disabled=disabled_tasks[5])
            ]),
        ]
    team_name = game.team_1_name if team == 1 else game.team_2_name
    players = game.team_1_players if team == 1 else game.team_2_players
    mentions = ', '.join(player.mention for player in players)
    msg = await game.channel.send(f'{mentions}\n{team_name}, select a greek letter to play {game_type}', components=components)
    ids = {player.id for player in players}
    btn = await msg.wait_for('button', client, check=lambda e: e.author.id in ids)
    selection = int(btn.data['custom_id'])
    await msg.edit(f'{team_name} selected {greek_letters[selection]}, starting {game_type}...', components=None)
    game_functions = {
        'connection': play_connection_or_sequence,
        'sequence': play_connection_or_sequence,
        'grid': play_grid
    }
    await game_functions[game_type](team_name, players, selection, game_type)


async def play_connection_or_sequence(team_name, players, selection, game_type):
    mentions = ', '.join(player.mention for player in players)
    components = [
        discord_ui.Button('next', custom_id='next'),
        discord_ui.Button(emoji='🔔', custom_id='buzzer', color='red')
    ]
    task = game.use_task(game_type, selection)
    embed = discord.Embed(title=f'{game_type} ({team_name})', description='60 seconds remaining', colour=0x5865f2)
    embed.add_field(name='5 Points', value=task[0], inline=True)
    t_start = time.time()
    remaining_time = 60

    class ConnectionListener(discord_ui.Listener):
        def __init__(self, timeout=config.t_connection, target_users=None):
            super().__init__(timeout, target_users)
            self.hints = 1
            self.game_ended = False

        @discord_ui.Listener.button('buzzer')
        async def on_buzz(self, ctx):
            if not self.game_ended:
                self.game_ended = True
                await msg.reply(f'{team_name} buzzed')
            await ctx.respond(ninja_mode=True)

        @discord_ui.Listener.button('next')
        async def on_next(self, ctx):
            hint_limit = 4 if game_type == 'connection' else 3
            if not self.game_ended and self.hints < hint_limit:
                points = 4 - self.hints
                msg.embeds[0].add_field(name=f'{points} Point{"s" if points > 1 else ""}', value=task[self.hints])
                await msg.edit(embed=msg.embeds[0])
                self.hints += 1
            await ctx.respond(ninja_mode=True)

    listener = ConnectionListener(target_users=players)
    msg = await game.channel.send(mentions, embed=embed, components=components, listener=listener)
    while not listener.game_ended and remaining_time > 0:
        remaining_time -= 10
        t_delay = t_start + config.t_connection - time.time() - remaining_time
        await asyncio.sleep(t_delay)
        msg.embeds[0].description = f'{remaining_time} seconds remaining'
        await msg.edit(embed=msg.embeds[0])
    if not listener.game_ended:
        listener.game_ended = True
        await msg.reply(f'{team_name} did not buzz in time')
    await msg.edit(components=None)


def play_grid(team_name, players, selection, game_type):
    pass


async def play_consonants(players):
    mentions = ', '.join(player.mention for player in players)
    ids = {player.id for player in players}
    for round_number in range(4):
        task = game.use_task('consonants', round_number)
        components = [discord_ui.Button(emoji='🔔', custom_id='buzzer', color='red')]
        embed = discord.Embed(title=f'consonants', description=task[0], colour=0x5865f2)
        msg = await game.channel.send(mentions, embed=embed, components=components)
        buzz_msg = None
        for word_number in range(4):
            btn = await msg.wait_for('button', client, check=lambda e: e.author.id in config.admins)
            await btn.respond(ninja_mode=True)
            if buzz_msg:
                await buzz_msg.delete()
            if word_number > 0:
                embed = discord.Embed(title=msg.embeds[0].title, description=msg.embeds[0].description)
                for field in msg.embeds[0].fields[:-1]:
                    embed.add_field(name=field.name, value=field.value, inline=False)
                embed.add_field(name=task[-1 + word_number * 2], value=task[word_number * 2], inline=False)
                await msg.edit(embed=embed)
                await asyncio.sleep(5)
            msg.embeds[0].add_field(name=task[1 + word_number * 2], value='\u200b', inline=False)
            await msg.edit(embed=msg.embeds[0])
            try:
                btn = await msg.wait_for('button', client, check=lambda e: e.author.id in ids, timeout=10)
                await btn.respond(ninja_mode=True)
                if btn.author in game.team_1_players:
                    team_name = game.team_1_name
                    team_mentions = ', '.join(player.mention for player in game.team_1_players)
                elif btn.author in game.team_2_players:
                    team_name = game.team_2_name
                    team_mentions = ', '.join(player.mention for player in game.team_2_players)
                else:
                    team_name = team_mentions = '???'
                buzz_msg = await msg.reply(f'{team_mentions}\n{team_name} buzzed')
            except asyncio.exceptions.TimeoutError:
                buzz_msg = await msg.reply(f'nobody buzzed in time')
        btn = await msg.wait_for('button', client, check=lambda e: e.author.id in config.admins)
        await buzz_msg.delete()
        await btn.respond(ninja_mode=True)


if __name__ == '__main__':
    client.run(config.bot_token)
