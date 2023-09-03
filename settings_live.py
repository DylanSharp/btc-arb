import os

from utils.aws import get_ssm_param, get_ssm_json_param

if os.environ.get('ACCOUNT_HOLDER'):
	ACCOUNT_HOLDER = logging_prefix = os.environ.get('ACCOUNT_HOLDER')
else:
	ACCOUNT_HOLDER = logging_prefix = input('Account holder:\n')
ACCOUNT_HOLDER = ACCOUNT_HOLDER.lower()

FIXER_API_KEY = get_ssm_param(name='fixer_api_key')
CLICKATEL_API_KEY = get_ssm_param(name='clickatel_api_key')
TWILIO_API_KEY = get_ssm_param(name='twilio_api_key')

gsuite_credentials = get_ssm_json_param(name='gsuite_credentials')

LUNO_ACCOUNT_CREDENTIALS = get_ssm_json_param('luno_account_credentials_{}'.format(ACCOUNT_HOLDER))
LUNO_BITCOIN_WITHDRAWAL_ADDRESS = get_ssm_param('luno_btc_withdrawal_address_{}'.format(ACCOUNT_HOLDER))

VALR_ACCOUNT_CREDENTIALS = get_ssm_json_param('valr_account_credentials_{}'.format(ACCOUNT_HOLDER))
VALR_BITCOIN_WITHDRAWAL_ADDRESS = get_ssm_param('valr_btc_withdrawal_address_{}'.format(ACCOUNT_HOLDER))

BITSTAMP_ACCOUNT_CREDENTIALS = get_ssm_json_param('bitstamp_account_credentials_{}'.format(ACCOUNT_HOLDER))

LOG_FILE_LOCATION = '/source/bitbot/logs/trade.log'
