import io
import os.path
from PIL import Image, ImageDraw, ImageFont

default_font_path	= os.path.join('res', 'DINMedium.ttf')
default_font_size	= 48
default_font	= ImageFont.truetype(default_font_path, default_font_size)
default_timer_font_size	= 36
blank_button	= Image.open(os.path.join('res', 'q.png'))
question_mark_button	= Image.open(os.path.join('res', 'qq.png'))
answer_bar	= Image.open(os.path.join('res', 'answer.png'))
timer_bar	= Image.open(os.path.join('res', 'timer.png'))
wall_colors	= list(map(lambda n: Image.open(os.path.join('res', f'wall_{n}.png')), [1, 2, 3, 4]))

def is_font_too_large(fs, texts, maxw, maxh):
	font = default_font if fs == default_font_size else ImageFont.truetype(default_font_path, fs)
	f_l, f_t, f_r, f_b = font.getbbox('Ág')
	fh = f_b - f_t
	if fh * len(texts) > maxh:
		return (True, font, fh)
	l = 0
	for text in texts:
		l = max(l, font.getlength(text))
	return (l > maxw, font, fh)

def find_font_size(texts, maxw, maxh):
	(too_large, font, fh) = is_font_too_large(default_font_size, texts, maxw, maxh)
	if too_large:
		low = 1
		hig = 48
		while hig > low + 1:
			mid = (low + hig) // 2
			(too_large2, font2, fh2) = is_font_too_large(mid, texts, maxw, maxh)
			if too_large2:
				hig = mid
			else:
				low = mid
				font = font2
				fh = fh2
	return font, fh

# stage:
# • 0 = first clue shown, timer shows 5 points
# • 1 = 2 clues shown, timer shows 3 points
# • 2 = 3 clues shown, timer shows 2 points (round 1 only)
# • 3 = 4 clues shown, timer shows 1 point (round 1 only)
# • 4 = 3 clues + “?” shown, timer shows 2 points (round 2 only)
# • 5 = 3 clues + “?” shown, timer shows 1 point (round 2 only)
# • 6 = everything shown (incl. answer), no timer
def gen_img(clues, answer_text, stage, filename=None):

	pad = 12	# padding between buttons
	w = 360	# width of a button
	h = 200	# height of a button
	mw = w - 24	# maximum width of the text on a button
	mh = h - 12	# maximum height of the text on a button
	tmh = 53	# height of the timer (top)
	ah = 89	# height of the answer bar (bottom)
	fo = 5	# adjustment by which text is moved down to make it look vertically centered

	tw = 4*w + 5*pad	# total width of the output bitmap
	th = 4*pad + tmh + h + ah	# total height of the output bitmap
	amw = tw - 2*pad - 12	# maximum width of the text on the answer bar
	amh = ah - 6	# maximum height of the text on the answer bar

	res = Image.new('RGB', (tw, th), (47, 49, 54))
	draw = ImageDraw.Draw(res)

	def gen_button(i, clue, tmr=None):
		x = (w + pad) * i + pad
		y = 2*pad + tmh
		if tmr is not None:
			res.paste(timer_bar, (x, pad), timer_bar)
			(too_large, font, fh) = is_font_too_large(default_timer_font_size, [tmr], mw, mh)
			l = font.getlength(tmr)
			draw.text((x + w//2 - l//2 + 2, pad + tmh//2 - fh//2 + fo + 2), tmr, font=font, fill=(0, 0, 0))
			draw.text((x + w//2 - l//2, pad + tmh//2 - fh//2 + fo), tmr, font=font, fill=(249, 254, 255))

		if clue is None:
			res.paste(question_mark_button, (x, y), question_mark_button)
		else:
			if clue.startswith('fullimage:'):
				img = Image.open(os.path.join('data', 'img', clue[10:]))
				img.thumbnail((w, h))
				try:
					res.paste(img, (x, y), img)
				except ValueError:
					res.paste(img, (x, y))
			elif clue.startswith('image:'):
				res.paste(blank_button, (x, y), blank_button)
				img = Image.open(os.path.join('data', 'img', clue[6:]))
				img.thumbnail((mw, mh))
				(iw, ih) = img.size
				try:
					res.paste(img, (x + w//2 - iw//2, y + h//2 - ih//2), img)
				except ValueError:
					res.paste(img, (x + w//2 - iw//2, y + h//2 - ih//2))
			else:
				res.paste(blank_button, (x, y), blank_button)
				lines = clue.split('\n')
				(font, fh) = find_font_size(lines, mw, mh)
				txh = fh * len(lines)
				txy = y + h//2 - txh//2
				for line, text in enumerate(lines):
					l = font.getlength(text)
					draw.text((x + w//2 - l//2, txy + fh*line + fo), text, font=font, fill=(5, 47, 85))

	if stage == 0:
		gen_button(0, clues[0], '5 points')
	elif stage == 1:
		gen_button(0, clues[0], None)
		gen_button(1, clues[1], '3 points')
	elif stage == 2:
		gen_button(0, clues[0], None)
		gen_button(1, clues[1], None)
		gen_button(2, clues[2], '2 points')
	elif stage == 3:
		gen_button(0, clues[0], None)
		gen_button(1, clues[1], None)
		gen_button(2, clues[2], None)
		gen_button(3, clues[3], '1 point')
	elif stage == 4:
		gen_button(0, clues[0], None)
		gen_button(1, clues[1], None)
		gen_button(2, clues[2], '2 points')
		gen_button(3, None, None)
	elif stage == 5:
		gen_button(0, clues[0], None)
		gen_button(1, clues[1], None)
		gen_button(2, clues[2], None)
		gen_button(3, None, '1 point')
	elif stage == 6:
		gen_button(0, clues[0], None)
		gen_button(1, clues[1], None)
		gen_button(2, clues[2], None)
		gen_button(3, clues[3], None)
		res.paste(answer_bar, (pad, 3*pad + tmh + h), answer_bar)
		(font, fh) = find_font_size([answer_text], amw, amh)
		l = font.getlength(answer_text)
		draw.text((tw//2 - l//2 + 2, 3*pad + tmh + h + ah//2 - fh//2 + fo + 2), answer_text, font=font, fill=(0, 0, 0))
		draw.text((tw//2 - l//2, 3*pad + tmh + h + ah//2 - fh//2 + fo), answer_text, font=font, fill=(249, 254, 255))

	image_file = open(filename, "wb") if filename is not None else io.BytesIO()
	res.save(image_file, 'PNG')
	image_file.seek(0)
	return image_file


def gen_wall(clues, num_done, selections, filename=None):

	pad = 12	# padding between buttons
	w = 360	# width of a button
	h = 200	# height of a button
	mw = w - 24	# maximum width of the text on a button
	mh = h - 12	# maximum height of the text on a button
	fo = 5	# adjustment by which text is moved down to make it look vertically centered
	tw = 4*w + 5*pad	# total width of the output bitmap
	th = 4*h + 5*pad	# total height of the output bitmap

	def gen_button(i, clue):
		x = (w + pad) * (i % 4) + pad
		y = (h + pad) * (i // 4) + pad

		btn = blank_button
		sel = False
		if i // 4 < num_done:
			btn = wall_colors[i // 4]
			sel = True
		elif i in selections:
			btn = wall_colors[num_done]
			sel = True

		res.paste(btn, (x, y), btn)
		lines = clue.split('\n')
		(font, fh) = find_font_size(lines, mw, mh)
		txh = fh * len(lines)
		txy = y + h//2 - txh//2
		for line, text in enumerate(lines):
			l = font.getlength(text)
			if sel:
				draw.text((x + w//2 - l//2, txy + fh*line + fo), text, font=font, fill=(255, 255, 255))
			else:
				draw.text((x + w//2 - l//2, txy + fh*line + fo), text, font=font, fill=(5, 47, 85))

	res = Image.new('RGB', (tw, th), (47, 49, 54))
	draw = ImageDraw.Draw(res)

	for i in range(16):
		gen_button(i, clues[i])

	image_file = open(filename, "wb") if filename is not None else io.BytesIO()
	res.save(image_file, 'PNG')
	image_file.seek(0)
	return image_file


