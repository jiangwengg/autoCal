def list_to_arr(string):
	arr = string.split('[')
	del arr[0]
	result = []
	for entry in arr:
		result.append(entry[0: -1])
	return result