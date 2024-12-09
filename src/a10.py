import time
import subprocess
import os
import cv2
import pytesseract
from datetime import datetime
from playwright.sync_api import sync_playwright
import numpy as np
import sys
from ppadb.client import Client as AdbClient
from TikTokApi import TikTokApi
from cleantext import clean
import re
import hashlib
from utils import *
import pandas as pd
import argparse
import random

# Coordinates for different engagements

MAX_X = 1080
MAX_Y = 1920
NEW_MAX_X = 720
NEW_MAX_Y = 1520
LIKE_Y = 775
SHARE_TOP_LEFT_X = 980/MAX_X
SHARE_TOP_LEFT_Y = 1415/MAX_Y
SHARE_BOTTOM_RIGHT_X = 1020/MAX_X
SHARE_BOTTOM_RIGHT_Y = 1550/MAX_Y
LINK_TOP_LEFT_X = 50/NEW_MAX_X
LINK_TOP_LEFT_Y = 1050/NEW_MAX_Y
LINK_BOTTOM_RIGHT_X = 150/NEW_MAX_X
LINK_BOTTOM_RIGHT_Y = 1200/NEW_MAX_Y
CLOSE_SHARE_X = 1000/MAX_X
CLOSE_SHARE_Y = 900/MAX_Y
WHY_TOP_LEFT_X = 450/MAX_X
WHY_TOP_LEFT_Y = 1600/MAX_Y
WHY_BOTTOM_RIGHT_X = 550/MAX_X
WHY_BOTTOM_RIGHT_Y = 1700/MAX_Y
CLOSE_WHY_TOP_LEFT_X = 200/MAX_X
CLOSE_WHY_TOP_LEFT_Y = 1750/MAX_Y
CLOSE_WHY_BOTTOM_RIGHT_X = 900/MAX_X
CLOSE_WHY_BOTTOM_RIGHT_Y = 1800/MAX_Y
SWIP_SHARE_MORE_X1 = 1000/MAX_X
SWIP_SHARE_MORE_X2 = 100/MAX_X
SWIP_SHARE_MORE_Y1 = 1350/MAX_Y
SWIP_SHARE_MORE_Y2 = 1350/MAX_Y
MORE_TOP_LEFT_X = 910/MAX_X
MORE_TOP_LEFT_Y = 1350/MAX_Y
MORE_BOTTOM_RIGHT_X = 990/MAX_X
MORE_BOTTOM_RIGHT_Y = 1400/MAX_Y
SWIPE_NEXT_VIDEO_X1 = 500
SWIPE_NEXT_VIDEO_X2 = 500
SWIPE_NEXT_VIDEO_Y1 = 900
SWIPE_NEXT_VIDEO_Y2 = 250

# Arguments for running the bot:
# device_name is the name of the Android device 
# username is the email address of the bot account
# metadata means if you want to retrieve TikTok video's metadata on the fly or not
# like, share, and follow represent the probabilities of randomly liking, sharing, or following the content creator of a video

parser = argparse.ArgumentParser()
parser.add_argument('--device_name', type=str, required=True)
parser.add_argument('--username', type=str, required=True)
parser.add_argument('--num_videos', type=int, required=True)
parser.add_argument('--metadata', type=int, required=True)
parser.add_argument('--like', type=float, required=False, default=0)
parser.add_argument('--share', type=float, required=False, default=0)
parser.add_argument('--follow', type=float, required=False, default=0)
args = parser.parse_args()
username = args.username
VIDEO_LIMIT = args.num_videos
device_name = args.device_name
retrieve_metadata = args.metadata
like_rate = args.like
share_rate = args.share
follow_rate = args.follow

email_address = username
email_hash = hashlib.md5(email_address.encode())
bot_directory = os.getcwd() + '/' + username

def swipe_next_video():

	command = 'input swipe {} {} {} {}'.format(SWIPE_NEXT_VIDEO_X1, SWIPE_NEXT_VIDEO_Y1, SWIPE_NEXT_VIDEO_X2, SWIPE_NEXT_VIDEO_Y2)
	print(command)
	device.shell(command)

def tap_on_share_icon():

	command = 'input tap {} {}'.format((SHARE_TOP_LEFT_X+SHARE_BOTTOM_RIGHT_X)/2*NEW_MAX_X, SHARE_TOP_LEFT_Y*NEW_MAX_Y)
	print(command)
	device.shell(command)
	time.sleep(0.5)

def tap_on_like_icon():

	command = 'input tap {} {}'.format((SHARE_TOP_LEFT_X+SHARE_BOTTOM_RIGHT_X)/2*NEW_MAX_X, LIKE_Y)
	print(command)
	device.shell(command)
	time.sleep(1)	

def tap_on_copy_link_icon(copy_link_x, copy_link_y):

	command = 'input tap {} {}'.format(copy_link_x+50, copy_link_y+75)
	print(command)
	device.shell(command)
	time.sleep(0.5)	

def tap_on_follow_icon(follow_x, follow_y):

	command = 'input tap {} {}'.format(follow_x, follow_y)
	print(command)
	device.shell(command)
	time.sleep(0.5)		

def screenshot(image_name):

	command = 'screencap -p /sdcard/' + image_name
	print(command)
	device.shell(command)

def pull_from_android(file_name, index, suffix):

	command = 'adb -s ' + device_name + ' pull /sdcard/' + file_name + suffix + ' ' + bot_directory + '/' + file_name + '_' + str(index) + suffix
	print(command)
	subprocess.run(command, shell=True)

def screenshot_save(file_name, index, suffix):

	location = bot_directory + '/' + file_name + '_' + str(index) + suffix
	print(location)
	result = device.screencap()
	with open(location, 'wb') as fp:
		fp.write(result)

def press_back():

	command = 'input keyevent 4'
	print(command)
	device.shell(command)

def get_link_from_clipboard(index):

	time.sleep(0.5)
	file_path = bot_directory + '/' + 'clipboard_' + str(index) + '.txt'
	subprocess.run('adb -s ' + device_name + ' shell am broadcast -n ch.pete.adbclipboard/.ReadReceiver > ' + file_path, shell=True)
	time.sleep(0.5)
	with open(file_path) as f:
		lines = f.readlines()
	return lines[1].split()[3][6:-1]

def inspect_for_why(file_name): # 0: NO WHY - 1: "Why this video" - 2: "About this ad"

	img = cv2.imread(bot_directory + '/' + file_name)
	question_logo_v1 = cv2.imread('question_logo_a10_v1.png')
	question_logo_v2 = cv2.imread('question_logo_a10_v2.png')
	copy_link_logo = cv2.imread('copy_link_logo_a10.png')
	start_x, start_y = 0, 0
	copy_link_x, copy_link_y = 0, 0
	found_copy_link = 0

	res = cv2.matchTemplate(img, copy_link_logo, cv2.TM_CCOEFF_NORMED)
	min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
	if max_val >= 0.99:
		copy_link_x = max_loc[0]
		copy_link_y = max_loc[1]
		found_copy_link = 1

	res_1 = cv2.matchTemplate(img, question_logo_v1, cv2.TM_CCOEFF_NORMED)
	min_val_1, max_val_1, min_loc_1, max_loc_1 = cv2.minMaxLoc(res_1)
	res_2 = cv2.matchTemplate(img, question_logo_v2, cv2.TM_CCOEFF_NORMED)
	min_val_2, max_val_2, min_loc_2, max_loc_2 = cv2.minMaxLoc(res_2)
	print(file_name)
	print(max_val, max_val_1, max_val_2)
	if max_val_1 >= 0.99:
		start_x = max_loc_1[0]
		start_y = max_loc_1[1]
	elif max_val_2 >= 0.99:
		start_x = max_loc_2[0]
		start_y = max_loc_2[1]		
	else:
		return 0, (start_x, start_y), found_copy_link, (copy_link_x, copy_link_y)
	split_text = pytesseract.image_to_string(img[start_y: start_y+150, start_x:start_x+100]).lower().split()
	required_terms_1 = ['why', 'this', 'video']
	required_terms_2 = ['about', 'this', 'ad']
	why_this_video = True
	for term in required_terms_1:
		if not term in split_text:
			why_this_video = False
	about_this_ad = True
	for term in required_terms_2:
		if not term in split_text:
			about_this_ad = False
	if why_this_video == True:
		return 1, (start_x, start_y), found_copy_link, (copy_link_x, copy_link_y)
	elif about_this_ad == True:
		return 2, (start_x, start_y), found_copy_link, (copy_link_x, copy_link_y)

def inspect_for_follow(file_name):

	img = cv2.imread(bot_directory + '/' + file_name)
	follow_logo = cv2.imread('follow_logo_a10_v1.png')
	img = img[:, 620:710]
	res = cv2.matchTemplate(img, follow_logo, cv2.TM_CCOEFF_NORMED)
	min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
	if max_val >= 0.95:
		x, y = max_loc[0], max_loc[1]
		return 1, (620 + x + 10, y + 10)
	follow_logo = cv2.imread('follow_logo_a10_v2.png')
	res = cv2.matchTemplate(img, follow_logo, cv2.TM_CCOEFF_NORMED)
	min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
	if max_val >= 0.95:
		x, y = max_loc[0], max_loc[1]
		return 1, (620 + x + 10, y + 10)
	return 0, (0, 0)

def inspect_for_live(file_name):

	img_rgb = cv2.imread(bot_directory + '/' + file_name)
	live_logo = cv2.imread('live_logo_resized_a10.png')

	res = cv2.matchTemplate(img_rgb, live_logo, cv2.TM_CCOEFF_NORMED)
	threshold = .8
	loc = np.where(res >= threshold)
	for pt in zip(*loc[::-1]):
		print('logo found')
		return True

	template = cv2.imread('tap_to_watch_live.png')
	template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
	template_blur = cv2.GaussianBlur(template_gray, (3,3), 0) 
	template_edges = cv2.Canny(image=template_blur, threshold1=100, threshold2=400)

	img = img_rgb[1050:1250, 200:500]
	img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
	img_blur = cv2.GaussianBlur(img_gray, (3,3), 0) 
	img_edges = cv2.Canny(image=img_blur, threshold1=100, threshold2=300) # Canny Edge Detection
	res = cv2.matchTemplate(img_edges, template_edges, cv2.TM_CCOEFF_NORMED)
	min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
	if max_val >= 0.7:
		return True

	favorite_logo = cv2.imread('favorite_logo_a10.png')
	favorite_edges = cv2.Canny(image=favorite_logo, threshold1=100, threshold2=200)

	like_logo = cv2.imread('like_logo_a10.png')
	like_edges = cv2.Canny(image=like_logo, threshold1=100, threshold2=200)

	comment_logo = cv2.imread('comment_logo_a10.png')
	comment_edges = cv2.Canny(image=comment_logo, threshold1=100, threshold2=200)

	share_logo = cv2.imread('share_logo_a10.png')
	share_edges = cv2.Canny(image=share_logo, threshold1=100, threshold2=200)	

	img_rgb = img_rgb[:, 600:]
	img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
	img_blur = cv2.GaussianBlur(img_gray, (3,3), 0) 
	img_edges = cv2.Canny(image=img_blur, threshold1=20, threshold2=50)

	res = cv2.matchTemplate(img_edges[900:1200, :], favorite_edges, cv2.TM_CCOEFF_NORMED)
	min_val, max_val_1, min_loc, max_loc = cv2.minMaxLoc(res)
	res = cv2.matchTemplate(img_edges[700:1000, :], like_edges, cv2.TM_CCOEFF_NORMED)
	min_val, max_val_2, min_loc, max_loc = cv2.minMaxLoc(res)
	res = cv2.matchTemplate(img_edges[800:1100, :], comment_edges, cv2.TM_CCOEFF_NORMED)
	min_val, max_val_3, min_loc, max_loc = cv2.minMaxLoc(res)
	res = cv2.matchTemplate(img_edges[1000:1300, :], share_edges, cv2.TM_CCOEFF_NORMED)
	min_val, max_val_4, min_loc, max_loc = cv2.minMaxLoc(res)

	print(max_val_1, max_val_2, max_val_3, max_val_4)
	score = max_val_1 + max_val_2 + max_val_3 + max_val_4

	if score >= 1.2:
		return False
	return True

def inspect_for_problem(file_name_1, file_name_2):

	img_1 = cv2.imread(bot_directory + '/' + file_name_1)
	img_2 = cv2.imread(bot_directory + '/' + file_name_2)
	res = cv2.matchTemplate(img_1, img_2, cv2.TM_CCOEFF_NORMED)
	min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
	print('Maximum similarity:', max_val)
	if max_val >= 0.95:
		return True
	return False

def inspect_for_language(file_name):

	img_rgb = cv2.imread(bot_directory + '/' + file_name)
	template = cv2.imread('languages_template_1.png')
	res = cv2.matchTemplate(img_rgb, template, cv2.TM_CCOEFF_NORMED)
	min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
	print('Maximum language template 1:', max_val)
	if max_val >= 0.8:
		return True
	template = cv2.imread('languages_template_2.png')
	res = cv2.matchTemplate(img_rgb, template, cv2.TM_CCOEFF_NORMED)
	min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
	print('Maximum language template 2:', max_val)
	if max_val >= 0.8:
		return True
	return False

def inspect_for_how(file_name):

	img_rgb = cv2.imread(bot_directory + '/' + file_name)
	template = cv2.imread('how_feel_a10.png')
	res = cv2.matchTemplate(img_rgb, template, cv2.TM_CCOEFF_NORMED)
	min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
	if max_val >= 0.95:
		return True
	return False	

def tap_on_about_take_screenshot_close_about(file_name, index, suffix, start_x, start_y):

	time.sleep(0.5)

	command = 'input tap {} {}'.format(start_x+50, start_y+75)
	print(command)
	device.shell(command)

	# wait for the tap to take place
	time.sleep(2.5)

	#screenshot(file_name + suffix)
	screenshot_save(file_name, index, suffix)

	press_back()

	#pull_from_android(file_name, index, suffix)

	# wait for the tap to take place
	time.sleep(0.5)

def tap_on_why_take_screenshot_close_why(file_name, index, suffix, start_x, start_y):

	time.sleep(0.5)
	
	command = 'input tap {} {}'.format(start_x+50, start_y+75)
	print(command)
	device.shell(command)

	# wait for the tap to take place
	time.sleep(2.5)

	#screenshot(file_name + suffix)
	screenshot_save(file_name, index, suffix)

	press_back()

	#pull_from_android(file_name, index, suffix)

	# wait for the tap to take place
	time.sleep(0.5)

def press_home():

	command = 'input keyevent 3'
	print(command)
	device.shell(command)

def extract_link(file_name):

	img_rgb = cv2.imread(file_name)
	template = cv2.imread('link_icon.png')
	w, h = template.shape[:-1]
	res = cv2.matchTemplate(img_rgb, template, cv2.TM_CCOEFF_NORMED)
	threshold = .8
	loc = np.where(res >= threshold)
	subimg = img_rgb[loc[::-1][1][0]:loc[::-1][1][0]+200, loc[::-1][0][0]+150:]
	text = pytesseract.image_to_string(subimg).split()
	s = ''
	for item in text:
		s = s+item
	return s

def fix_hashtags(row):

	hashtags = row
	hashtags_aggregate = []
	for hashtag in hashtags:
		hashtags2 = ['#' + x for x in hashtag.split('#')] 
		for h in hashtags2:
			if len(h)>1:
				hashtags_aggregate.append(h)
	return hashtags_aggregate
		
def extract_hashtags(s):

	s = clean(s, no_emoji=True)
	hashs = list(set([re.sub(r"#+", "#", k) for k in set([re.sub(r"(\W+)$", "", j, flags = re.UNICODE) for j in set([i for i in s.split() if i.startswith("#")])])]))
	hashs2 = [x for x in hashs if len(x)>1]
	fixed_hashs = fix_hashtags(hashs2)
	return fixed_hashs

def get_explanations(file_name):

	img_rgb = cv2.imread(bot_directory + '/' + file_name)
	template = cv2.imread('why_you_see_this_video_a10.png')

	res = cv2.matchTemplate(img_rgb, template, cv2.TM_CCOEFF_NORMED)
	threshold = .8
	loc = np.where(res >= threshold)

	subimg = img_rgb[loc[::-1][1][0]:, loc[::-1][0][0]:]
	text = pytesseract.image_to_string(subimg)

	return text

def get_current_video_index():

	# Exception when folder exists but dataframe does not exist

	if not os.path.exists(bot_directory):
		os.makedirs(bot_directory)
		return 0
	else:
		df = pd.read_json(bot_directory + '/' + 'dataframe_' + username + '.json', dtype={'video_id': str})
		return len(df)

def connect():
	client = AdbClient(host="127.0.0.1", port=5037) # Default is "127.0.0.1" and 5037
	devices = client.devices()
	if len(devices) == 0:
		print('No devices')
		quit()
	#device = devices[0]
	device = client.device(device_name)
	return device, client

if __name__ == '__main__':

	device, client = connect()

	go_on = True
	cnt = 0
	prev_live = False

	try:

		while go_on == True:

			json_dataframe = []
			current_video_index = get_current_video_index()

			start_time_string = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
			start_time_date = datetime.strptime(start_time_string, "%Y-%m-%d %H:%M:%S")

			time.sleep(1)

			screenshot_save('check_live', current_video_index, '.png')
			#screenshot('check_live.png')
			#pull_from_android('check_live', current_video_index, '.png')

			res = inspect_for_how('check_live_' + str(current_video_index) + '.png')

			if res == True:
				print("Sorry, how do you feel detected. Throwing an exception.")
				raise Exception("Sorry, how do you feel detected. Throwing an exception.")

			res = inspect_for_language('check_live_' + str(current_video_index) + '.png')

			if res == True:
				print('Language detected - pressing back button')
				press_back()
				time.sleep(2)
				screenshot_save('check_live', current_video_index, '.png')
				print('Language detected - taking new screenshot')

			if current_video_index >= 1:
				res = inspect_for_problem('check_live_' + str(current_video_index) + '.png', 'check_live_' + str(current_video_index-1) + '.png')
				if res == True:
					print("Sorry, similar videos observed. Throwing an exception.")
					raise Exception("Sorry, similar videos observed. Throwing an exception.")

			res = inspect_for_live('check_live_' + str(current_video_index) + '.png')

			found_follow_button, (follow_x, follow_y) = inspect_for_follow('check_live_' + str(current_video_index) + '.png')

			# Checking if the current TikTok video is "live"

			if res == True:
				print('LIVE')

				end_time_string = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
				end_time_date = datetime.strptime(end_time_string, "%Y-%m-%d %H:%M:%S")

				dataframe_object = {
					'date': start_time_string,
					'explanations': 'LIVE VIDEO',
					'end_date': end_time_string
				}

				print(dataframe_object)
				json_dataframe.append(dataframe_object)
				Utils.create_json(json_dataframe, 'dataframe_' + username, username)

				if prev_live == True:
					print("Sorry, two consecutive live videos! Throwing an exception.")
					raise Exception("Sorry, two consecutive live videos! Throwing an exception.")
				prev_live = True

				cnt += 1
				if cnt >= VIDEO_LIMIT:
					go_on = False
				if go_on == True:
					swipe_next_video()

			# If the current TikTok video is NOT a "live" video

			else:
				print('NOT LIVE')
				prev_live = False

				
				
				tap_on_share_icon()
				
				# wait for the tap to take place
				time.sleep(1)

				
				screenshot_save('check_video', current_video_index, '.png')
				#screenshot('check_video.png')
				#pull_from_android('check_video', current_video_index, '.png')
				
				res, (start_x, start_y), found_copy_link, (copy_link_x, copy_link_y) = inspect_for_why('check_video_' + str(current_video_index) + '.png')
				print('Found \"Why this video\"?: ', res)

				if res == 0:
					press_back()
					time.sleep(0.5)
					explanations_text = None
				elif res == 1:
					tap_on_why_take_screenshot_close_why('explanations', current_video_index, '.png', start_x, start_y)
					explanations_text = get_explanations('explanations_' + str(current_video_index) + '.png')
					print(explanations_text)
				elif res == 2:
					tap_on_about_take_screenshot_close_about('explanations', current_video_index, '.png', start_x, start_y)
					explanations_text = 'Ad'
					print(explanations_text)

				

				if retrieve_metadata == 2 and found_copy_link == 1:

					video_id_retrieved = False
					while video_id_retrieved == False:

						tap_on_share_icon()
						tap_on_copy_link_icon(copy_link_x, copy_link_y)
						link = get_link_from_clipboard(current_video_index)
						print(link)

						with sync_playwright() as p:
							browser = p.firefox.launch(headless=True, slow_mo=50)
							context = browser.new_context()
							page = context.new_page()
							for idx in range(5):
								done = False
								try:
									page.goto(link)
									done = True
								except:
									pass
								if done == False:
									time.sleep(2)
								else:
									break
							print(page.url)
							video_url = page.url

						if len(video_url.split('/')) == 6:
							protocol, space, site, user, video, video_id = video_url.split('/')
							user = user.replace('@', '')
							video_id, *_ = video_id.split('?')
							print(user, video_id)
							video_id_retrieved = True

					with TikTokApi() as api:
						for idx in range(5):
							done = False
							try:
								video = api.video(id=video_id)
								metadata = video.info_full()
								done = True
							except:
								pass
							if done == False:
								time.sleep(2)
							else:
								break

					video_description = metadata['itemInfo']['itemStruct']['desc']
					video_duration = metadata['itemInfo']['itemStruct']['video']['duration']
					video_creator = metadata['itemInfo']['itemStruct']['author']['uniqueId']
					video_hashtags = extract_hashtags(video_description)

					end_time_string = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
					end_time_date = datetime.strptime(end_time_string, "%Y-%m-%d %H:%M:%S")

					inferred_duration = (end_time_date - start_time_date).total_seconds()
					if video_duration > 0:
						viewing_duration_percentage = inferred_duration/video_duration*100
					else:
						viewing_duration_percentage = 0
					video_watched_till_end = (inferred_duration >= video_duration+1)

					dataframe_object = {
						'video_id': video_id, 
						'date': start_time_string,
						'video_url': video_url,
						'video_link': link,
						'end_date': end_time_string, 
						'inferred_duration': inferred_duration, 
						'video_duration': video_duration, 
						'viewing_duration_percentage': viewing_duration_percentage, 
						'video_watched_till_end': video_watched_till_end,
						'hashtags': video_hashtags,
						'num_hashtags': len(video_hashtags),
						'video_creator': video_creator,
						'liked_on': False,
						'followed_on': False,
						'video_from_following': False,
						'email_md5': email_hash.hexdigest(),
						'metadata': metadata,
						'explanations': explanations_text
					}

				else:

					liked_on = False
					if res == 0 or res == 1:
						prob = random.random()
						if prob <= like_rate and like_rate != 0:
							tap_on_like_icon()
							liked_on = True

					link = None
					if (res == 0 or res == 1) and found_copy_link == 1:
						prob = random.random()
						if prob <= share_rate and share_rate != 0:
							tap_on_share_icon()
							tap_on_copy_link_icon(copy_link_x, copy_link_y)
							link = get_link_from_clipboard(current_video_index)
							print(link)

					followed_on = False
					if (res == 0 or res == 1) and found_follow_button == 1:
						prob = random.random()
						if prob <= follow_rate and follow_rate != 0:
							tap_on_follow_icon(follow_x, follow_y)
							followed_on = True

					screenshot_save('check_end', current_video_index, '.png')

					print('Liked or not:', liked_on)
					print('Followed or not:', followed_on)

					end_time_string = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
					end_time_date = datetime.strptime(end_time_string, "%Y-%m-%d %H:%M:%S")

					dataframe_object = {
						'video_id': None, 
						'date': start_time_string,
						'video_url': None,
						'video_link': link,
						'end_date': end_time_string, 
						'inferred_duration': None, 
						'video_duration': None, 
						'viewing_duration_percentage': None, 
						'video_watched_till_end': None,
						'hashtags': None,
						'num_hashtags': 0,
						'video_creator': None,
						'liked_on': liked_on,
						'followed_on': followed_on,
						'video_from_following': False,
						'email_md5': email_hash.hexdigest(),
						'metadata': None,
						'explanations': explanations_text
					}

				print(dataframe_object)
				json_dataframe.append(dataframe_object)
				Utils.create_json(json_dataframe, 'dataframe_' + username, username)

				cnt += 1
				if cnt >= VIDEO_LIMIT:
					go_on = False

				if go_on == True:
					swipe_next_video()

		press_home()

	except Exception as e:

		print('Failed: '+ str(e))
		press_home()