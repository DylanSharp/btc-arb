import logging
import math
import time
from logging.handlers import RotatingFileHandler

import art
from r7insight import R7InsightHandler

from integrations.pushover import send_notification
from integrations.twilio import send_sms
from settings import ACCOUNT_HOLDER, LOG_FILE_LOCATION

logger = logging.getLogger("Rotating Log")
logger.setLevel(logging.INFO)

# add a rotating handler
handler = RotatingFileHandler(
	filename=LOG_FILE_LOCATION,
	maxBytes=1024 * 1024 * 10,  # 10MB
	backupCount=100
)

formatter = logging.Formatter('{} : %(asctime)s : %(levelname)s : %(message)s'.format(ACCOUNT_HOLDER))
handler.setFormatter(formatter)
logger.addHandler(handler)

# Setup R7 Logging.

r7_logger = logging.getLogger('r7insight')
r7_logger.setLevel(logging.INFO)
r7_handler = R7InsightHandler('11d3fc3d-f83c-4dd5-b406-4f4ed3343092', 'eu')
r7_handler.setFormatter(formatter)

r7_logger.addHandler(r7_handler)

spacer = '#' * 100


def log(msg, level='i', notify=False, color=None, as_art=False):
	try:
		# Ensure that incoming messages are strings because they might be exceptions, ints or floats.
		msg = str(msg)

		if level == 'i':
			logger.info(msg)
			r7_logger.info(msg)
		elif level == 'd':
			logger.debug(msg)
			r7_logger.debug(msg)
		elif level == 'w':
			logger.warning(msg)
			r7_logger.warning(msg)
		elif level == 'e':
			logger.error(msg)
			r7_logger.error(msg)

		if notify:
			# If notification breaks send
			try:
				send_notification(msg)
			except ValueError:
				send_sms(msg)

		# Add color before printing.
		msg = set_color(msg, color)
		if as_art:
			print_art(msg)
		else:
			print(msg)
	except Exception as e:
		# The logger should never cause a catastrophic exceptions.
		print(e)


def byte_encode(input):
	return bytes(input, encoding='utf-8')


def round_down(n, decimals=0):
	multiplier = 10 ** decimals
	return math.floor(n * multiplier) / multiplier


def print_art(text, color=None):
	try:
		output = art.text2art(text)
		if color:
			output = set_color(output, color)
		print(output)
	except Exception:
		# Never let an art print kill the app.
		pass


def set_color(msg, color=None):
	if color == 'red':
		color_code = '\x1b[31m'
	elif color == 'yellow':
		color_code = '\x1b[33m'
	elif color == 'blue':
		color_code = '\x1b[34m'
	elif color == 'magenta':
		color_code = '\x1b[35m'
	elif color == 'cyan':
		color_code = '\x1b[36m'
	elif color == 'green':
		color_code = '\x1b[92m'
	elif color == 'purple':
		color_code = '\x1b[35m'
	else:
		return msg
	return color_code + msg + '\x1b[0m'


def wait(seconds=1):
	time.sleep(seconds)


if __name__ == '__main__':
	for i in range(1, 3):
		log('Test {}'.format(i))
