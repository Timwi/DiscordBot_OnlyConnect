import tasks

task_amounts = {'connection': 6, 'sequence': 6, 'grid': 2, 'grid_finals': 2, 'missing_vowels': 4}


class Game:
    def __init__(self):
        self.team_1_name = None
        self.team_1_players = None
        self.team_2_name = None
        self.team_2_players = None
        self.channel = None
        self.tasks = {game_type: tasks.load_tasks(game_type, n_tasks, one_image=(game_type in ('connection', 'sequence'))) for game_type, n_tasks in task_amounts.items()}

    def disabled_tasks(self, game_type):
        return [task_tuple is None for task_tuple in self.tasks[game_type]]

    def use_task(self, game_type, selection):
        task_id, task = self.tasks[game_type][selection]
        self.tasks[game_type][selection] = None
        tasks.mark_task_used(game_type, task_id)
        return task
