import io
import os.path
import random
import time
import asyncio
import uuid
import math
import json
import discord
import config

from discord.ext import commands
from game import Game
from discord import app_commands
from PIL import Image, ImageOps, ImageDraw, ImageFont
from genimg import gen_img

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
if __name__ == '__main__':
	client.run(config.bot_token)

@client.event
async def on_ready():
	status += f'logged in as {client.user}\n'



f = io.open("data/data.json", mode="r", encoding="utf-8")
game = json.load(f)

hieroglyphs = ["Two reeds", "Lion", "Twisted Flax", "Horned Viper", "Water", "Eye of Horus"]
wall_hieroglyphs = ["Lion", "Water"]


@client.tree.command(name='status', description='show game status')
async def show_next(interaction: discord.Interaction):
	global game
	if interaction.user.id not in config.admins:
		await interaction.response.send_message('You are not hosting!', ephemeral=True)
		return
	status_str = '**Status:**\n'
	if game.ongoing is None:
		status_str += 'There is no game in progress. Use `/addteam` and `/delteam` to setup teams, then use `/teams` to define who’s playing, then use `/play` to play each round. Use `/cancel` to delete the current game in progress.'
	else:
		status_str += 'Current teams:\n'
		for teamN, teamIx in enumerate(game.ongoing.teams):
			team = game.teams[teamIx]
			status_str += f'    - [score: {team.score}] {"▶ " if game.ongoing.up == teamN else ""}{team.name} ({", ".join(team.players)})\n'
		status_str += f'Current batch: {game.ongoing.batch}\n'
		status_str += 'Current round:\n'
		status_str += f'    - {["Connections", "Sequences", "Connecting Wall", "Missing Vowels"][game.ongoing.round]}\n'
		if game.ongoing.round < 2:
			status_str += f'    - Used: {", ".join(map(lambda u: hieroglyphs[u], game.ongoing.used))}\n'
			status_str += f'    - Available: {", ".join(map(lambda u: hieroglyphs[u], [x for x in range(6) if x not in game.ongoing.used]))}\n'
		elif game.ongoing.round == 2:
			status_str += f'    - Used: {", ".join(map(lambda u: wall_hieroglyphs[u], game.ongoing.used))}\n'
			status_str += f'    - Available: {", ".join(map(lambda u: wall_hieroglyphs[u], [x for x in range(2) if x not in game.ongoing.used]))}\n'
		else: # game.ongoing.round == 3:
			status_str += f'    - Categories played: {game.ongoing.played}\n'
	await interaction.response.send_message(status_str, ephemeral=True)

@client.tree.command(name='flip', description='flip a coin')
async def flip(interaction: discord.Interaction):
	result = random.choice(['heads', 'tails'])
	await interaction.response.send_message(result)

def save_game():
	global game
	with open("data/data.json", 'w', encoding='utf-8') as f:
		json.dump(game, f, ensure_ascii=False, indent=4)

@client.tree.command(name='addteam', description='add a team')
async def addteam(	interaction: discord.Interaction,
	name: str,
	player_1: discord.Member,
	player_2: discord.Member,
	player_3: discord.Member):

	global game
	if interaction.user.id not in config.admins:
		await interaction.response.send_message('You are not hosting!', ephemeral=True)
		return
	players = [player_1.id]
	if player_2.id not in players:
		players.append(player_2.id)
	if player_3.id not in players:
		players.append(player_3.id)
	game.teams.append({"name": name, "players": [player_1.id, player_2.id, player_3.id], "score": 0})
	save_game()
	await interaction.response.send_message('A new team joined! Team name: **{}**, members: {}'.format(name, ", ".join(f'<@{p}>' for p in players)))

def indexof(lst, fnc):
	for i, elem in enumerate(lst):
		if fnc(elem):
			return i
	return None

@client.tree.command(name='delteam', description='delete a team')
@app_commands.choices(name=[app_commands.Choice(name=name, value=value) for value, name in enumerate(game.teams)])
async def delteam(	interaction: discord.Interaction,
	name: str):

	global game
	if interaction.user.id not in config.admins:
		await interaction.response.send_message('You are not hosting!', ephemeral=True)
		return
	ix = indexof(game.teams, lambda t: t.name == name)
	if ix is None:
		await interaction.response.send_message(f'No team with that name exists.', ephemeral=True)
	else:
		t = game.teams[ix]
		await interaction.response.send_message('Team **{}** has left the game: {}, score: {t.score}'.format(t.name, ", ".join(f'<@{p}>' for p in t.players)))

@client.tree.command(name='teams', description='select teams for the next game (team 1 goes first)')
@app_commands.choices(team1=[app_commands.Choice(name=name, value=value) for value, name in enumerate(game.teams)])
@app_commands.choices(team2=[app_commands.Choice(name=name, value=value) for value, name in enumerate(game.teams)])
async def teams(	interaction: discord.Interaction,
	team1: str,
	team2: str):

	global game
	if interaction.user.id not in config.admins:
		await interaction.response.send_message('You are not hosting!', ephemeral=True)
		return
	if game.ongoing is not None:
		await interaction.response.send_message('There is already a game in progress. Use `/cancel` to abort that game.')
		return
	ix1 = indexof(game.teams, lambda t: t.name == team1)
	if ix1 is None:
		await interaction.response.send_message(f'No team with the name **{team1}** exists.', ephemeral=True)
		return
	ix2 = indexof(game.teams, lambda t: t.name == team2)
	if ix2 is None:
		await interaction.response.send_message(f'No team with the name **{team2}** exists.', ephemeral=True)
		return
	batchIx = indexof(range(len(game.batches)), lambda t: t not in game.batches_used)
	if batchIx is None:
		await interaction.response.send_message('There are no more unused question batches.', ephemeral=True)
		return
	game.ongoing = { round: 0, teams: [ix1, ix2], used: [], batch: batchIx, up: 0 }
	save_game()
	await interaction.response.send_message('Game configured. Use `/play` to start.', ephemeral=True)

@client.tree.command(name='play', description='Resume the current game')
async def play(interaction: discord.Interaction):
	if interaction.user.id not in config.admins:
		await interaction.response.send_message('You are not hosting!', ephemeral=True)
		return
	if game.ongoing is None:
		await interaction.response.send_message(f'No game configured. Use `/addteam` to set up the teams and `/teams` to select the teams for the game. Then use `/play` again to start.', ephemeral=True)
		return
	await interaction.response.send_message('Not implemented.', ephemeral=True)
	# await select_greek_letter(team, game_type)


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


async def play_connection_or_sequence(team_name, players, other_players, selection, game_type):
	isRound2 = game_type == 'sequence'
	mentions = ', '.join(player.mention for player in players)
	task = game.use_task(game_type, selection)
	for other_player in other_players:
		try:
			await other_player.edit(deafen=True)
		except discord.HTTPException:
			pass
	t_start = time.time()
	remaining_time = config.t_connection
	buzz_event = asyncio.Event()
	done_event = asyncio.Event()
	buzzer_id = str(uuid.uuid4())

	class ConnectionListener(discord.ui.View):
		def __init__(self, target_users):
			super().__init__(timeout=None)
			self.target_users = target_users
			self.stage = 0
			self.buzzed = False

		@discord.ui.button(emoji='🔔', custom_id=buzzer_id, style=discord.ButtonStyle.red)
		async def on_buzz(self, interaction: discord.Interaction, button: discord.ui.Button):
			# During timer: players buzzed
			if not self.buzzed and interaction.user in self.target_users:
				self.buzzed = True
				await msg.reply(f'{mentions}\n{team_name} buzzed')
				buzz_event.set()
				for other_player_2 in other_players:
					try:
						await other_player_2.edit(deafen=False)
					except discord.HTTPException:
						pass
				await interaction.response.defer()

			# After timer: admin presses buzzer ⇒ reveal all answers
			elif self.buzzed and interaction.user.id in config.admins:
				self.stage = 6
				done_event.set()
				await interaction.response.defer()
				await self.generate()

			else:
				await interaction.response.send_message('😠', ephemeral=True)


		@discord.ui.button(label='next')
		async def on_next(self, interaction: discord.Interaction, button: discord.ui.Button):
			# During timer: players pressed Next
			if not self.buzzed and interaction.user in self.target_users:
				if self.stage < 3:
					if isRound2 and self.stage == 1:
						self.stage = 4
					else:
						self.stage += 1
					await self.generate()
				await interaction.response.defer()

			# After timer: admin presses Next to show remaining clues and give bonus chance to opposing team
			elif self.buzzed and interaction.user.id in config.admins:
				self.stage = 5 if isRound2 else 3
				await interaction.response.defer()
				await self.generate()

			else:
				await interaction.response.send_message('😠', ephemeral=True)


		async def generate(self):
			file = discord.File(gen_img(task, task[4], self.stage), filename=f'clues{self.stage}.png')
			msg.embeds[0].set_image(url=f'attachment://clues{self.stage}.png')
			await msg.edit(embed=msg.embeds[0], attachments=[file])

	listener = ConnectionListener(target_users=players)

	embed = discord.Embed(title=f'{"Round 2: Sequences" if isRound2 else "Round 1: Connections"} ({team_name})', description='60 seconds remaining', colour=0x5865f2)
	embed.set_image(url=f'attachment://clues0.png')
	file = discord.File(gen_img(task, task[4], 0), filename=f'clues0.png')
	msg = await game.channel.send(mentions, embed=embed, view=listener, file=file)

	while not listener.buzzed and remaining_time > 0:
		if remaining_time > 10:
			remaining_time -= 10
		else:
			remaining_time -= 1
		elapsed = time.time() - t_start
		used_time = config.t_connection - remaining_time
		t_delay = used_time - elapsed
		try:
			await asyncio.wait_for(buzz_event.wait(), timeout=t_delay)
		except asyncio.exceptions.TimeoutError:
			msg.embeds[0].description = f'{remaining_time} seconds remaining' if remaining_time > 0 else f'Time’s up!'
			await msg.edit(embed=msg.embeds[0])
	if not listener.buzzed:
		listener.buzzed = True
		await msg.reply(f'{team_name} did not buzz in time.')
		for other_player in other_players:
			try:
				await other_player.edit(deafen=False)
			except discord.HTTPException:
				pass

	await asyncio.wait_for(done_event.wait(), timeout=None)
	listener.stop()


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
		msg = await game.channel.send(mentions, embed=embed, view=parent_view)
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
				buzz_msg = await msg.reply(f'{team_mentions} — :bellhop: {team_name} buzzed')
			except asyncio.exceptions.TimeoutError:
				buzz_msg = await msg.reply(f'Nobody buzzed in time.')

