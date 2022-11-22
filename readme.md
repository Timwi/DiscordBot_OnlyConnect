# Discord Only Connect Bot
The bot shows predefined tasks to teams of three players, similar to the game show Only Connect.
Players can interact with the bot to buzz in answers and advance clues.
A game host (admin) manually confirms the answers and tracks points.
This bot was written hastily for a specific event and isn't very advanced or polished.
The tasks in `tasks` were written by @weaver and @Catz for our event and are included
as en example/template.

## Setup

1. Checkout and install the bot
   ````sh
   git clone https://github.com/RasmusAntons/discord_onlyconnect.git
   cd discord_only_connect
   python -m venv venv
   . venv/bin/acticate
   pip install -r requirements.txt
   ````

2. Edit `config.py`: Set bot token, guild id and admin ids.

3. Edit tasks:
    Use LibreOffice Calc or MS Excel to edit the `tasks/*.csv` files. Each line contains one task.
    The order of the tasks within a file will be randomised, the order of answers inside a task is fixed.
    The line numbers of still available tasks is stored in a JSON file analogous to the csv file.
    If the JSON file does not exist it is created with all line numbers by the `/init` command.
    This can be reset by deleting the JSON file.

5. Run the bot
   ```sh
   python main.py
   ```

## Commands
The bot provides 3 slash commands to run games.

### `/init`
  First, set up the teams with `/init`.
  This chooses a set of tasks the teams can select with the greek letters.
  * `team_1_name` Name of the first team
  * `team team_1_player_1` First player on the first team
  * `team_1_player_2` Second player on the first team (repeat first player if less than two players)
  * `team_1_player_3` Third player on the first team (repeat second player if less than three players)
  * `team_1_name` Name of the second team
  * `team team_1_player_1` First player on the second team
  * `team_1_player_2` Second player on the second team (repeat first player if less than two players)
  * `team_1_player_3` Third player on the second team (repeat second player if less than three players)

### `/flip`
Then decide which team goes first, you can use `/flip` to do that, which simulates a coin flip.

### `/play`
   Finally, start each game round with the `/play` command.
   This removes the tasks line number from the JSON file, so it will not be chosen again.
   In the case of missing_vowels, 4 rounds will automatically be played in succession.
  * `team` The number of the team playing this round (ignored for missing_vowels)
  * `game_type` The name of the game (one of `connections`, `sequence`, `grid`, `grid_finals`, `missing_vowels`)

Assuming team 1 starts, a typical game would look like this:
   ```
   /play 1 connection
   /play 2 connection
   /play 1 connection
   /play 2 connection
   /play 1 connection
   /play 2 connection
   /play 1 sequence
   /play 2 sequence
   /play 1 sequence
   /play 2 sequence
   /play 1 sequence
   /play 2 sequence
   /play 1 grid
   /play 2 grid
   /play 1 missing_vowels
   ```

## Game types

### Connection
The tasks are defined in `tasks/connection.csv`. The first four columns contain the four clues in order.
The fifth column contains the connection (solution).
After the playing team buzzed or time (60s) runs out, an admin can click the buzzer to reveal unused clues.
Then an admin can click the buzzer again to reveal the connection.

### Sequence
The tasks are defined in `tasks/sequence.csv`. The first three columns contain the three clues in order.
The fourth column contains the sought element (solution).
The fifth column contains the connection (explanation of the sequence).
After the playing team buzzed or time (60s) runs out, an admin can click the buzzer to reveal unused clues.
Then an admin can click the buzzer again to reveal the sought element and the connection.

### Grid and Grid finals
The tasks are defined in `tasks/grid.csv` and `tasks/grid_finals.csv`.
There is no functional difference between the two game modes, we used them to reserve specific (harder) grids
for the last games.
Each line contains a puzzgrid.com URL.
When the playing team chooses a greek letter, the URL is sent to all admins.
The idea is for one team member to screenshare their browser, the admin forwards the link to that team member
and the team collaboratively solves the grid using the timer on the site.

### Missing vowels
The tasks are defined in `tasks/missing_vowels.csv`.
The first column contains the category that is shown before each round.
The remaining eight columns alternately contain a task (prompt without vowels and changed spaces)
and the solution.
After one team buzzes or the time (10s) runs out, an admin can click the buzzer to reveal the solution,
wait 5 seconds and then show the next prompt.
While the show uses a fixed amount of time for this category,
the bot will always play four rounds of four prompts each.

## TODO
Would be nice if the bot could keep track of scores by having admins click `correct` or `incorrect` buttons
after a team buzzes or time runs out.
The bot could also just run all rounds of a game automatically instead of an admin calling `/play` 15 times.
I don't know if I will implement that in the future, maybe if we want to use the bot again.
