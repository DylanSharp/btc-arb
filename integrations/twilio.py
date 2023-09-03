import requests
from requests.auth import HTTPBasicAuth

from settings import TWILIO_API_KEY

TWILIO_SANDBOX_NUMBER = '+14155238886'
TWILIO_BITBOT_NUMBER = '+27600703126'


def _get_auth():
	return HTTPBasicAuth('ACb5f80da13619892009a7bc5880614af3', TWILIO_API_KEY)


def send_whatsapp(body, to='+27741821742'):
	"""
	:param to: The number to send to in the format +27741821742
	:param body: The message
	:return:
	"""
	to = 'whatsapp:{}'.format(to)
	_from = 'whatsapp:{}'.format(TWILIO_SANDBOX_NUMBER)
	res = requests.post(
		'https://api.twilio.com/2010-04-01/Accounts/ACb5f80da13619892009a7bc5880614af3/Messages.json',
		auth=_get_auth(),
		data={
			'From': _from,
			'To': to,
			'Body': body,
		})
	return res


def send_sms(body, to='+27741821742'):
	"""
	:param to: The number to send to in the format +27741821742
	:param body: The message
	:return:
	"""
	to = '{}'.format(to)
	_from = '{}'.format(TWILIO_BITBOT_NUMBER)
	res = requests.post(
		'https://api.twilio.com/2010-04-01/Accounts/ACb5f80da13619892009a7bc5880614af3/Messages.json',
		auth=_get_auth(),
		data={
			'From': _from,
			'To': to,
			'Body': body,
		})
	return res


if __name__ == '__main__':
	send_whatsapp('My message.')
