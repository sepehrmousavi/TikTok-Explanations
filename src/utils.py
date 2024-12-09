import json
import os
import os.path

class Utils:
	@staticmethod
	def create_json(json_list, name, directory):
		data = []
		# Checking if the file already exists
		final_dir = os.getcwd() + '/' + directory
		if not os.path.exists(final_dir):
			os.makedirs(final_dir)
		file_list = os.listdir(final_dir)

		if name+'.json' in file_list:
			# Open the file, if it does not exist, it is created
			with open(final_dir+'/'+name+".json", "r") as file:
				data = json.load(file)
		# Update json object
		data = data + json_list
		json_object = json.dumps(data, indent=2)  # put data instead of json_list
		# Update json file
		with open(final_dir+'/'+name+".json", "w") as outfile:
			outfile.write(json_object)
