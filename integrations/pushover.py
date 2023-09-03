import urllib

import requests
from requests.auth import HTTPBasicAuth

from settings import TWILIO_API_KEY

PUSHOVER_APP_TOKEN = 'av9a65irpdu7qnmjdqdsj6b67g5woa'
PUSHOVER_USER_KEY = 'u3fgket4wtkkyr4u7p23yvgz94nify'


def _get_auth():
	return HTTPBasicAuth('ACb5f80da13619892009a7bc5880614af3', TWILIO_API_KEY)


def send_notification(message, device='device_1', title=''):
	"""
	:param message: The message.
	:param device: The device to send to.
	:param title: Optional title.
	:return:
	"""
	data = {
		'token': PUSHOVER_APP_TOKEN,
		'user': PUSHOVER_USER_KEY,
		'device': device,
		'title': title,
		'message': message
	}
	url = 'https://api.pushover.net/1/messages.json?{}'.format(urllib.parse.urlencode(data))
	res = requests.post(url)
	if res.status_code != 200:
		raise ValueError('Pushover did not return a 200 response.')
	return res


if __name__ == '__main__':
	send_notification('My message.', title='Test')
