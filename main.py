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
from discord import app_commands
from PIL import Image, ImageOps, ImageDraw, ImageFont
from genimg import gen_img, gen_wall, gen_wall_full, gen_missing_vowels, gen_score, gen_scores
from utils import indexof

with io.open("data/data.json", mode="r", encoding="utf-8") as f:
	game = json.load(f)

hieroglyphs = ["𓇌   Two Reeds", "𓃭   Lion", "𓎛   Twisted Flax", "𓆑   Horned Viper", "𓈗   Water", "𓂀   Eye of Horus"]
wall_hieroglyphs = ["𓃭   Lion", "𓈗   Water"]


def save_game():
	global game
	with open("data/data.json", 'w', encoding='utf-8') as df:
		json.dump(game, df, ensure_ascii=False, indent=4)

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

@client.event
async def on_ready():
	print(f'logged in as {client.user}')

#	  / ╓──┐┌─╥─┐╓──╖┌─╥─┐╥  ╥ ╓──┐
#	 /  ╙──╖  ║  ╟──╢  ║  ║  ║ ╙──╖
#	/   └──╜  ╨  ╨  ╨  ╨  ╙──╜ └──╜
@client.tree.command(name='status', description='show game status')
async def show_next(interaction: discord.Interaction):
	global game
	if interaction.user.id not in config.admins:
		await interaction.response.send_message('You are not hosting!', ephemeral=True)
		return
	status_str = '**Status:**\n'
	if game['ongoing'] is None:
		status_str += 'There is no game in progress. Use `/addteam` and `/delteam` to setup teams, then use `/start` to define who’s playing, then use `/play` to play each round. Use `/cancel` to delete the current game in progress.'
	else:
		status_str += 'Current teams:\n'
		for teamN, teamIx in enumerate(game['ongoing']['teams']):
			team = game['teams'][teamIx]
			status_str += f'    - [score: {game["ongoing"]["scores"][teamN]}] {"▶ " if game["ongoing"]["round"] < 3 and game["ongoing"]["up"] == teamN else ""}{team["name"]} ({", ".join("<@{}>".format(t) for t in team["players"])})\n'
		status_str += f'Current batch: {game["ongoing"]["batch"]}\n'
		status_str += 'Current round:\n'
		status_str += f'    - {["Connections", "Sequences", "Connecting Wall", "Missing Vowels"][game["ongoing"]["round"]]}\n'
		if game['ongoing']['round'] < 2:
			status_str += f'    - Used: {", ".join(map(lambda u: hieroglyphs[u], game["ongoing"]["used"]))}\n'
			status_str += f'    - Available: {", ".join(map(lambda u: hieroglyphs[u], [x for x in range(6) if x not in game["ongoing"]["used"]]))}\n'
		elif game['ongoing']['round'] == 2:
			status_str += f'    - Used: {", ".join(map(lambda u: wall_hieroglyphs[u], game["ongoing"]["used"]))}\n'
			status_str += f'    - Available: {", ".join(map(lambda u: wall_hieroglyphs[u], [x for x in range(2) if x not in game["ongoing"]["used"]]))}\n'
		else: # game['ongoing']['round'] == 3
			status_str += f'    - Categories played: {game["ongoing"]["category"]}\n'
	await interaction.response.send_message(status_str, ephemeral=True)

#	  / ╥──┐╥   ╥ ╥─╖
#	 /  ╟─┤ ║   ║ ╟─╜
#	/   ╨   ╨──┘╨ ╨
@client.tree.command(name='flip', description='flip a coin')
async def flip(interaction: discord.Interaction):
	result = random.choice(['heads', 'tails'])
	file_name = os.path.join('res', 'coins', f"{result}{random.randrange(0, 5) + 1}.png")
	df = discord.File(open(file_name, 'rb'), filename=f"{result}.png")
	await interaction.response.send_message(file=df)

#	  / ╓──╖ ─╥─╖ ─╥─╖┌─╥─┐╥──┐ ╓──╖ ╥┐┌╥
#	 /  ╟──╢  ║ ║  ║ ║  ║  ╟─┤  ╟──╢ ║└┘║
#	/   ╨  ╨ ─╨─╜ ─╨─╜  ╨  ╨──┘ ╨  ╨ ╨  ╨
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
	game['teams'].append({"name": name, "players": players, "score": 0})
	save_game()
	await interaction.response.send_message('A new team joined! Team name: **{}**, members: {}'.format(name, ", ".join(f'<@{p}>' for p in players)))

#	  / ─╥─╖ ╥──┐ ╥  ┌─╥─┐╥──┐ ╓──╖ ╥┐┌╥
#	 /   ║ ║ ╟──  ║    ║  ╟─┤  ╟──╢ ║└┘║
#	/   ─╨─╜ ╨──┘ ╨──┘ ╨  ╨──┘ ╨  ╨ ╨  ╨
@client.tree.command(name='delteam', description='delete a team')
@app_commands.choices(index=[app_commands.Choice(name=team['name'], value=i) for i, team in enumerate(game['teams'])])
async def delteam(	interaction: discord.Interaction,
	index: int):

	global game
	if interaction.user.id not in config.admins:
		await interaction.response.send_message('You are not hosting!', ephemeral=True)
		return
	if index < 0 or index >= len(game['teams']):
		await interaction.response.send_message('Invalid team index.', ephemeral=True)
		return
	t = game['teams'][index]
	del game['teams'][index]
	save_game()
	await interaction.response.send_message('Team **{}** has left the game: {}, score: {}'.format(t['name'], ", ".join(f'<@{p}>' for p in t['players']), t['score']))

#	  / ╓──┐┌─╥─┐╓──╖ ╥──╖┌─╥─┐
#	 /  ╙──╖  ║  ╟──╢ ╟─╥╜  ║
#	/   └──╜  ╨  ╨  ╨ ╨ ╙─  ╨
@client.tree.command(name='start', description='select teams for the next game (team 1 goes first)')
@app_commands.choices(team1=[app_commands.Choice(name=team['name'], value=i) for i, team in enumerate(game['teams'])])
@app_commands.choices(team2=[app_commands.Choice(name=team['name'], value=i) for i, team in enumerate(game['teams'])])
async def start(	interaction: discord.Interaction,
	team1: int,
	team2: int):

	global game
	if interaction.user.id not in config.admins:
		await interaction.response.send_message('You are not hosting!', ephemeral=True)
		return
	if game['ongoing'] is not None:
		await interaction.response.send_message('There is already a game in progress. Use `/cancel` (erase) or `/finish` (add scores and then erase) first.', ephemeral=True)
		return
	if team1 < 0 or team1 >= len(game['teams']) or team2 < 0 or team2 >= len(game['teams']):
		await interaction.response.send_message('Invalid team index.', ephemeral=True)
		return
	batch_index = indexof(range(len(game['batches'])), lambda t: t not in game['batches_used'])
	if batch_index is None:
		await interaction.response.send_message('There are no more unused question batches.', ephemeral=True)
		return
	game['ongoing'] = { 'round': 0, 'teams': [team1, team2], 'scores': [0, 0], 'used': [], 'batch': batch_index, 'up': 0 }
	game['batches_used'].append(batch_index)
	save_game()
	await interaction.response.send_message('Game configured. Use `/play` to start.', ephemeral=True)

#	  / ┌─╥─┐╥──┐ ╓──╖ ╥┐┌╥ ╓──┐
#	 /    ║  ╟─┤  ╟──╢ ║└┘║ ╙──╖
#	/     ╨  ╨──┘ ╨  ╨ ╨  ╨ └──╜
@client.tree.command(name='teams', description='List all teams')
async def score(interaction: discord.Interaction):
	global game
	if interaction.user.id not in config.admins:
		await interaction.response.send_message('You are not hosting!', ephemeral=True)
		return

	teams_str = '**__Teams__:**\n'
	for team in game['teams']:
		teams_str += f"**{team['name']}**: {', '.join(f'<@{p}>' for p in team['players'])}\n"

	await interaction.response.send_message(teams_str)

#	  / ╓──┐ ╓──┐ ╓──╖ ╥──╖ ╥──┐ ╓──┐
#	 /  ╙──╖ ║    ║  ║ ╟─╥╜ ╟─┤  ╙──╖
#	/   └──╜ ╙──┘ ╙──╜ ╨ ╙─ ╨──┘ └──╜
@client.tree.command(name='scores', description='Display the current scores')
async def scores(interaction: discord.Interaction):
	global game
	if interaction.user.id not in config.admins:
		await interaction.response.send_message('You are not hosting!', ephemeral=True)
		return
	if game['ongoing'] is None:
		await interaction.response.send_message('No ongoing game.', ephemeral=True)
		return

	await interaction.response.send_message(
		file=discord.File(gen_score(
			[game['teams'][game['ongoing']['teams'][ix]]['name'] for ix in range(2)],
			game['ongoing']['scores']),
		filename="scores.png"))

#	  / ╥──┐╥  ╥ ╥   ╥   ╓──┐ ╓──┐ ╓──╖ ╥──╖ ╥──┐ ╓──┐
#	 /  ╟─┤ ║  ║ ║   ║   ╙──╖ ║    ║  ║ ╟─╥╜ ╟─┤  ╙──╖
#	/   ╨   ╙──╜ ╨──┘╨──┘└──╜ ╙──┘ ╙──╜ ╨ ╙─ ╨──┘ └──╜
@client.tree.command(name='fullscores', description='Display the overall scores of all teams')
async def scores(interaction: discord.Interaction):
	global game
	if interaction.user.id not in config.admins:
		await interaction.response.send_message('You are not hosting!', ephemeral=True)
		return
	await interaction.response.send_message(file=discord.File(gen_scores(game['teams']), filename="scores.png"))

#	  / ╓──┐ ╓──╖ ╥╖ ╥ ╓──┐ ╥──┐ ╥
#	 /  ║    ╟──╢ ║╙╖║ ║    ╟─┤  ║
#	/   ╙──┘ ╨  ╨ ╨ ╙╨ ╙──┘ ╨──┘ ╨──┘
@client.tree.command(name='cancel', description='Cancel the current game (discard all progress and scores)')
async def score(interaction: discord.Interaction):
	global game
	if interaction.user.id not in config.admins:
		await interaction.response.send_message('You are not hosting!', ephemeral=True)
		return
	if game['ongoing'] is None:
		await interaction.response.send_message('No ongoing game.', ephemeral=True)
		return
	print("ERASING:")
	print(game['ongoing'])
	game['ongoing'] = None
	save_game()
	await interaction.response.send_message('Game progress erased. Use `/start` to start a new game.', ephemeral=True)

#	  / ╥──┐╥ ╥╖ ╥ ╥ ╓──┐ ╥  ╥
#	 /  ╟─┤ ║ ║╙╖║ ║ ╙──╖ ╟──╢
#	/   ╨   ╨ ╨ ╙╨ ╨ └──╜ ╨  ╨
@client.tree.command(name='finish', description='Finish the current game (add scores to team overall scores)')
async def score(interaction: discord.Interaction):
	global game
	if interaction.user.id not in config.admins:
		await interaction.response.send_message('You are not hosting!', ephemeral=True)
		return
	if game['ongoing'] is None:
		await interaction.response.send_message('No ongoing game.', ephemeral=True)
		return
	print("ERASING:")
	print(game['ongoing'])
	game['teams'][game['ongoing']['teams'][0]]['score'] += game['ongoing']['scores'][0]
	game['teams'][game['ongoing']['teams'][1]]['score'] += game['ongoing']['scores'][1]
	game['ongoing'] = None
	save_game()
	await interaction.response.send_message('Game finished. Use `/start` to start a new game.', ephemeral=True)

#     / ╓──┐ ╥ ╥  ╥ ╥──┐
#    /  ║ ─╖ ║ ╙╖╓╜ ╟─┤
#   /   ╙──╜ ╨  ╙╜  ╨──┘
@client.tree.command(name='give', description='give points to a team (or take away if negative)')
@app_commands.choices(team=[app_commands.Choice(name='first team', value=0), app_commands.Choice(name='second team', value=1)])
async def start(	interaction: discord.Interaction,
	team: int,
	addscore: int):

	global game
	if game['ongoing'] is None:
		await interaction.response.send_message('No ongoing game.', ephemeral=True)
		return
	game['ongoing']['scores'][team] += addscore
	save_game()
	await interaction.response.send_message('Scores adjusted.', ephemeral=True)

#	  / ╥─╖ ╥   ╓──╖ ╥ ╥
#	 /  ╟─╜ ║   ╟──╢ ╙╥╜
#	/   ╨   ╨──┘╨  ╨  ╨
@client.tree.command(name='play', description='Resume the current game')
async def play(interaction: discord.Interaction):
	global game
	if interaction.user.id not in config.admins:
		await interaction.response.send_message('You are not hosting!', ephemeral=True)
		return
	if game['ongoing'] is None:
		await interaction.response.send_message('No game configured. Use `/addteam` to set up the teams and `/start` to select the teams for the game. Then use `/play` again to play.', ephemeral=True)
		return

	async def run_missing_vowels(round, round_name, response=None):
		global game
		players1	= game['teams'][game['ongoing']['teams'][0]]['players']
		players2	= game['teams'][game['ongoing']['teams'][1]]['players']
		players	= [*players1, *players2]

		vw = discord.ui.View(timeout=None)

		buzzer_id = str(uuid.uuid4())
		correct_id = str(uuid.uuid4())
		wrong_id = str(uuid.uuid4())

		vw.add_item(discord.ui.Button(emoji='🔔', custom_id=buzzer_id, style=discord.ButtonStyle.red))
		vw.add_item(discord.ui.Button(label='✓', custom_id=correct_id))
		vw.add_item(discord.ui.Button(label='✗', custom_id=wrong_id))

		embed = discord.Embed(title=round_name, description='', colour=0x5865f2)
		embed.set_image(url='attachment://mv.png')
		file = discord.File(gen_missing_vowels(round['category'], []), filename='mv.png')
		if response:
			await response.send_message(embed=embed, files=[file], view=vw)
		else:
			await interaction.channel.send(embed=embed, files=[file], view=vw)

		qs = []

		for q_index, q in enumerate(round['clues']):
			# Wait for host to press buzzer to show next clue
			btn_click = await client.wait_for('interaction',
				check=lambda e: e.data.get('custom_id') == buzzer_id and e.user.id in config.admins, timeout=None)

			# Display clue
			print(f"{q['clue']} ==> {q['answer']}")
			qs.append(q['clue'])
			file = discord.File(gen_missing_vowels(round['category'], qs), filename='mv.png')
			await btn_click.response.edit_message(embed=embed, attachments=[file], view=vw)

			# Wait for someone to buzz or host to press ✗
			btn_click = await client.wait_for('interaction',
				check=lambda e: (e.data.get('custom_id') == buzzer_id and e.user.id in players) or (e.data.get('custom_id') == wrong_id and e.user.id in config.admins), timeout=None)

			if btn_click.data['custom_id'] == buzzer_id:

				team_ix = 0 if btn_click.user.id in players1 else 1
				embed.description = f'🔔 BUZZED: {game["teams"][game["ongoing"]["teams"][team_ix]]["name"]}'
				await btn_click.response.edit_message(embed=embed)

				# Wait for host to press ✓ or ✗
				btn_click = await client.wait_for('interaction',
					check=lambda e: e.data.get('custom_id') in [correct_id, wrong_id] and e.user.id in config.admins, timeout=None)

				if btn_click.data['custom_id'] == correct_id:
					game['ongoing']['scores'][team_ix] += 1
					save_game()
				else:
					game['ongoing']['scores'][team_ix] -= 1
					save_game()

					# throw it to the other team for a bonus
					team_ix = team_ix ^ 1
					embed.description = f'💎 Bonus: {game["teams"][game["ongoing"]["teams"][team_ix]]["name"]}'
					await btn_click.response.edit_message(embed=embed)
					btn_click = await client.wait_for('interaction',
						check=lambda e: e.data.get('custom_id') in [correct_id, wrong_id] and e.user.id in config.admins, timeout=None)

					if btn_click.data['custom_id'] == correct_id:
						game['ongoing']['scores'][team_ix] += 1
						save_game()

				embed.description = ''

			# Show answer
			qs[-1] = q['answer']
			file = discord.File(gen_missing_vowels(round['category'], qs), filename='mv.png')
			await btn_click.response.edit_message(embed=embed, attachments=[file], view=None if q_index == len(round['clues']) - 1 else vw)


	# CONNECTIONS or SEQUENCES (rounds 1 and 2)

	if game['ongoing']['round'] < 2:
		isSeq	= game['ongoing']['round']	== 1
		team	= game['teams'][game['ongoing']['teams'][game['ongoing']['up']]]
		guild	= client.get_guild(config.guild_id)
		players	= [guild.get_member(id) or await client.fetch_user(id) for id in team['players']]
		other_team	= game['teams'][game['ongoing']['teams'][game['ongoing']['up'] ^ 1]]
		other_players	= [guild.get_member(id) or await client.fetch_user(id) for id in other_team['players']]
		mentions	= " ".join(f"<@{p}>" for p in team["players"]);

		# select an Egyptian hieroglyph
		vw = discord.ui.View(timeout=None)
		btn_ids = []
		for i in range(6):
			btn_id = str(uuid.uuid4())
			btn_ids.append(btn_id)
			vw.add_item(discord.ui.Button(
				label=hieroglyphs[i], custom_id=btn_id, disabled=i in game['ongoing']['used'],
				row=(i // 3), style=discord.ButtonStyle.primary))
		await interaction.response.send_message(f'{mentions}\n**{team["name"]}**, select an Egyptian hieroglyph.', view=vw)
		btn_click: discord.Interaction = await client.wait_for('interaction', check=lambda e: e.data.get('custom_id') in btn_ids and e.user.id in team['players'], timeout=None)
		selection = btn_ids.index(btn_click.data['custom_id'])
		await btn_click.response.edit_message(content=f'**{team["name"]}** selected __{hieroglyphs[selection]}__. **Get ready!**', view=None)

		# Connections/Sequences game starts here
		q = game['batches'][game['ongoing']['batch']]['sequences' if isSeq else 'connections'][selection]
		print(f"───────────────────────────────────────────────────\n{q['answer']}\n\n")
		for clue in q['clues']:
			print(clue)
		if q['notes'] is not None and len(q['notes']) > 0:
			print(f"\n{q['notes']}\n")

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

		embed = discord.Embed(title=f'{"Round 2: Sequences" if isSeq else "Round 1: Connections"} ({team["name"]})', description='🕛 60 seconds remaining', colour=0x5865f2)
		embed.set_image(url=f'attachment://clues0.png')

		class ConnectionListener(discord.ui.View):
			def __init__(self, target_users):
				super().__init__(timeout=None)
				self.target_users = target_users
				self.stage = 0
				self.other = False
				self.buzzed = False

			@discord.ui.button(emoji='🔔', custom_id=buzzer_id, style=discord.ButtonStyle.red)
			async def on_buzz(self, interaction: discord.Interaction, button: discord.ui.Button):
				global game

				# During timer: players buzzed
				if not self.buzzed and interaction.user in self.target_users:
					self.buzzed = True
					buzz_event.set()
					embed.description=f'🔔 BUZZED: {team["name"]}'
					await interaction.response.edit_message(embed=embed)

				# After timer: admin presses buzzer ⇒ reveal all answers and award points
				elif self.buzzed and interaction.user.id in config.admins:
					team_to_award = other_team if self.other else team
					num_points = [5, 3, 2, 1, 2, 1][self.stage]
					game['ongoing']['scores'][game['ongoing']['up'] ^ (1 if self.other else 0)] += num_points
					save_game()
					self.stage = 6
					await self.generate(interaction.response, f'✔ {team_to_award["name"]} earns {num_points} point{"s" if num_points > 1 else ""}!')
					done_event.set()
				else:
					await interaction.response.send_message('You are not hosting!', ephemeral=True)


			@discord.ui.button(label='next')
			async def on_next(self, interaction: discord.Interaction, button: discord.ui.Button):
				# During timer: players pressed Next
				if not self.buzzed and interaction.user in self.target_users:
					if self.stage < 3:
						if isSeq and self.stage == 1:
							self.stage = 4
						else:
							self.stage += 1
					await self.generate(interaction.response)

				# After timer: admin presses Next to show remaining clues and give bonus chance to opposing team
				elif self.buzzed and interaction.user.id in config.admins:
					self.stage = 5 if isSeq else 3
					self.other = True
					await self.generate(interaction.response, descr=f'💎 Bonus: {other_team["name"]}')

				else:
					await interaction.response.send_message('You are not hosting!', ephemeral=True)

			@discord.ui.button(label='✗')
			async def on_wrong(self, interaction: discord.Interaction, button: discord.ui.Button):
				# Wrong answer ⇒ reveal all answers (no points awarded)
				if self.other and interaction.user.id in config.admins:
					self.stage = 6
					await self.generate(interaction.response, descr='')
					done_event.set()
				else:
					await interaction.response.send_message('You are not hosting!', ephemeral=True)

			async def generate(self, response, descr=None):
				file = discord.File(gen_img(q, self.stage), filename=f'clues{self.stage}.png')
				embed.set_image(url=f'attachment://clues{self.stage}.png')
				if descr is not None:
					embed.description = descr
				await response.edit_message(embed=embed, attachments=[file], view=None if self.stage == 6 else listener)

		listener = ConnectionListener(target_users=players)

		file = discord.File(gen_img(q, 0), filename=f'clues0.png')
		msg = await interaction.channel.send(mentions, embed=embed, files=[file], view=listener)

		while not listener.buzzed and remaining_time > 0:
			if remaining_time > 5:
				remaining_time -= 5
			else:
				remaining_time -= 1
			elapsed = time.time() - t_start
			used_time = config.t_connection - remaining_time
			t_delay = used_time - elapsed
			try:
				await asyncio.wait_for(buzz_event.wait(), timeout=t_delay)
			except asyncio.exceptions.TimeoutError:
				if not listener.buzzed:
					embed.description = f'{["🕛", "🕚", "🕙", "🕘", "🕗", "🕖", "🕕", "🕔", "🕓", "🕒", "🕑", "🕐"][(remaining_time//5) % 12]} {remaining_time} seconds remaining' if remaining_time > 0 else f'❌ Time’s up!'
					await msg.edit(embed=embed)

		for other_player in other_players:
			try:
				await other_player.edit(deafen=False)
			except discord.HTTPException:
				pass

		listener.buzzed = True

		await asyncio.wait_for(done_event.wait(), timeout=None)
		listener.stop()

		# advance to the next question or round
		game['ongoing']['up'] = game['ongoing']['up'] ^ 1
		game['ongoing']['used'].append(selection)
		if len(game['ongoing']['used']) == 6:
			game['ongoing']['round'] = game['ongoing']['round'] + 1
			game['ongoing']['used'] = []
		save_game()


	# CONNECTING WALL (round 3)

	elif game['ongoing']['round'] == 2:
		team	= game['teams'][game['ongoing']['teams'][game['ongoing']['up']]]
		guild	= client.get_guild(config.guild_id)
		players	= [guild.get_member(id) or await client.fetch_user(id) for id in team['players']]
		mentions	= " ".join(f"<@{p}>" for p in team["players"]);

		# select an Egyptian hieroglyph
		vw = discord.ui.View(timeout=None)
		btn_ids = []
		for i in range(2):
			btn_id = str(uuid.uuid4())
			btn_ids.append(btn_id)
			vw.add_item(discord.ui.Button(
				label=wall_hieroglyphs[i], custom_id=btn_id, disabled=i in game['ongoing']['used'],
				row=0, style=discord.ButtonStyle.primary))
		msg = await interaction.response.send_message(f'{mentions}\n**{team["name"]}**, select an Egyptian hieroglyph.', view=vw)
		btn_click: discord.Interaction = await client.wait_for('interaction', check=lambda e: e.data.get('custom_id') in btn_ids and e.user.id in team['players'], timeout=None)
		selection = btn_ids.index(btn_click.data['custom_id'])
		await btn_click.response.edit_message(content=f'**{team["name"]}** selected **{wall_hieroglyphs[selection]}!**', view=None)

		# Output the wall to the console
		wall = game['batches'][game['ongoing']['batch']]['walls'][selection]
		longest_answer = max(len(gr['answer']) for gr in wall['groups'])
		longest_clue = max(max(len(c) for c in gr['clues']) for gr in wall['groups'])
		print("───────────────────────────────────────────────────")
		print(wall['url'])
		for group in wall['groups']:
			print(f"{group['answer'].ljust(longest_answer)} │ {' '.join(c.ljust(longest_clue) for c in group['clues'])}")
		print("")

		# Send the Puzzgrid link to the player
		dm_channel = btn_click.user.dm_channel or await btn_click.user.create_dm()
		try:
			await dm_channel.send(f'Connecting Wall for {team["name"]}: <{wall["url"]}>')
		except discord.HTTPException:
			pass

		# Allow host to select number of points
		vw = discord.ui.View(timeout=None)
		points = [0, 1, 2, 3, 4, 5, 6, 7, 10]
		btn_ids = []
		for pts in points:
			btn_id = str(uuid.uuid4())
			btn_ids.append(btn_id)
			vw.add_item(discord.ui.Button(
				label=str(pts), custom_id=btn_id, style=discord.ButtonStyle.primary))
		msg = await interaction.channel.send('Number of points earned:', view=vw)
		btn_click = await client.wait_for('interaction', check=lambda e: e.data.get('custom_id') in btn_ids and e.user.id in config.admins, timeout=None)
		num_points = points[btn_ids.index(btn_click.data['custom_id'])]
		game['ongoing']['scores'][game['ongoing']['up']] += num_points

		file = discord.File(gen_wall_full(wall), filename='wall.png')
		embed = discord.Embed(title='Round 3: Connecting Wall', colour=0x5865f2)
		embed.set_image(url='attachment://wall.png')
		await btn_click.response.edit_message(content=f'**{team["name"]}** earned **__{num_points} points__!**', embed=embed, attachments=[file], view=None)

		# advance to the next wall or round
		game['ongoing']['up'] = game['ongoing']['up'] ^ 1
		game['ongoing']['used'].append(selection)
		if len(game['ongoing']['used']) == 2:
			game['ongoing']['round'] = 3
			game['ongoing']['category'] = 0
			del game['ongoing']['used']
			del game['ongoing']['up']
		save_game()


	# MISSING VOWELS (round 4)

	elif game['ongoing']['category'] < len(game['batches'][game['ongoing']['batch']]['missing_vowels']):
		first = True
		for round_ix, round in enumerate(game['batches'][game['ongoing']['batch']]['missing_vowels']):
			if round_ix >= game['ongoing']['category']:
				await run_missing_vowels(round, 'Round 4: Missing Vowels', response=interaction.response if first else None)
				game['ongoing']['category'] += 1
				save_game()
				first = False


	# TIE BREAKER

	elif game['ongoing']['scores'][0] == game['ongoing']['scores'][1]:
		tie_index = indexof(range(len(game['tie_breakers'])), lambda t: t not in game['tie_breakers_used'])
		if tie_index is None:
			await interaction.response.send_message('There are no more unused tie breakers.')
			return
		game['tie_breakers_used'].append(tie_index)
		save_game()
		await run_missing_vowels({ "category": "TIE BREAKER", "clues": [game['tie_breakers'][tie_index]] }, 'TIE BREAKER', response=interaction.response)


	else:
		await interaction.response.send_message('The game is over. Use `/finish` to transfer the scores to the overall leaderboard. Then use `/start` to set up a new game.', ephemeral=True)


if __name__ == '__main__':
	client.run(config.bot_token)
