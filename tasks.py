import csv
import json
import os.path
import random


def load_tasks(game_type, n_tasks):
    with open(f'tasks/{game_type}.csv') as f:
        available_tasks = dict(enumerate(csv.reader(f)))
    if os.path.exists(f'tasks/{game_type}.json'):
        with open(f'tasks/{game_type}.json') as f:
            unused_tasks = json.load(f)
    else:
        unused_tasks = list(available_tasks.keys())
        with open(f'tasks/{game_type}.json', 'w') as f:
            json.dump(unused_tasks, f)
    return [(i, available_tasks[i]) for i in random.sample(unused_tasks, k=n_tasks)]


def mark_task_used(game_type, task_id):
    with open(f'tasks/{game_type}.json') as f:
        unused_tasks = json.load(f)
    unused_tasks.remove(task_id)
    with open(f'tasks/{game_type}.json', 'w') as f:
        json.dump(unused_tasks, f)
