import base64
import io
import json
import pyperclip

from genimg import gen_img, gen_wall, gen_wall_full, gen_missing_vowels, gen_score, gen_scores

f = io.open("data/data.json", mode="r", encoding="utf-8")
game = json.load(f)

html = """<style>
	html {
		background: #2F3136;
		text-align: center;
	}
	img {
		margin: .5cm 2cm;
	}
</style>
<body>
"""

for batch in game['batches']:
	if len(batch['connections']) != 6:
		print(f"Connections is bad: {len(batch['connections'])}; first is {batch['connections'][0]['answer']}")
	if len(batch['sequences']) != 6:
		print(f"Sequences is bad: {len(batch['sequences'])}; first is {batch['sequences'][0]['answer']}")
	if len(batch['walls']) != 2:
		print(f"Walls is bad: {len(batch['walls'])}; first is {batch['walls'][0]['url']}")
	if len(batch['missing_vowels']) != 4:
		print(f"Missing Vowels is bad: {len(batch['missing_vowels'])}; first is {batch['missing_vowels'][0]['category']}")
	for q in batch['connections']:
		io_stream = gen_img(q, 6)
		html += f'<img src="data:image/png;base64,{base64.b64encode(io_stream.getvalue()).decode()}" />\n'
	html += '<br><hr><br>\n'
html += '<hr>\n\n'

for batch in game['batches']:
	for q in batch['sequences']:
		io_stream = gen_img(q, 6)
		html += f'<img src="data:image/png;base64,{base64.b64encode(io_stream.getvalue()).decode()}" />\n'
	html += '<br><hr><br>\n'
html += '<hr>\n\n'

for batch in game['batches']:
	for wall in batch['walls']:
		io_stream = gen_wall_full(wall)
		html += f'<img src="data:image/png;base64,{base64.b64encode(io_stream.getvalue()).decode()}" />\n'
	html += '<br><hr><br>\n'

html += "</body>"

with open("view.html", "w") as text_file:
	text_file.write(html)