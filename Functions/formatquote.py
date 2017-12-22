def format_quote(afloat):
	if len(str(afloat).split('.')[0]) == 3:
		return int(str(afloat).split('.')[0])
	elif len(str(afloat).split('.')[0]) == 2:
		return '{:>.1f}'.format(afloat)
	else:
		return '{:>.2f}'.format(afloat)
