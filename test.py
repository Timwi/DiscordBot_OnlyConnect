import json
import io
from genimg import gen_img

name = "Executioners"
players = [47, 8472, 24567837]

print('A new team joined! Team name: **{}**, members: {}'.format(name, ", ".join(f'<@{p}>' for p in players)))