import csv
import json
import os.path
import random


def load_tasks(game_type, n_tasks, one_image=False):
    with open(f'tasks/{game_type}.csv') as f:
        available_tasks = dict(enumerate(csv.reader(f)))
    if os.path.exists(f'tasks/{game_type}.json'):
        with open(f'tasks/{game_type}.json') as f:
            unused_tasks = json.load(f)
    else:
        unused_tasks = list(available_tasks.keys())
        with open(f'tasks/{game_type}.json', 'w') as f:
            json.dump(unused_tasks, f)
    image_task = None
    if one_image:
        all_tasks = unused_tasks
        image_tasks = []
        unused_tasks = []
        for task in all_tasks:
            if task[0].startswith('image:'):
                image_tasks.append(task)
            else:
                unused_tasks.append(task)
        if image_tasks:
            image_task = random.choice(image_tasks)
    n_normal_tasks = n_tasks if image_task else n_tasks - 1
    chosen_tasks = [(i, available_tasks[i]) for i in random.sample(unused_tasks, k=min(n_normal_tasks, len(unused_tasks)))]
    if image_task:
        chosen_tasks.append(image_task)
        random.shuffle(chosen_tasks)
    if len(chosen_tasks) < n_tasks:
        chosen_tasks.extend([None] * (n_tasks - len(unused_tasks)))
    return chosen_tasks


def mark_task_used(game_type, task_id):
    with open(f'tasks/{game_type}.json') as f:
        unused_tasks = json.load(f)
    unused_tasks.remove(task_id)
    with open(f'tasks/{game_type}.json', 'w') as f:
        json.dump(unused_tasks, f)
