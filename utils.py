def indexof(lst, fnc):
	for i, elem in enumerate(lst):
		if fnc(elem):
			return i
	return None

#client.tree.remove_command('flip')
