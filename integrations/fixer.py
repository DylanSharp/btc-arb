import requests

from utils.helpers import retry
from settings import FIXER_API_KEY

ACCESS_KEY_PARAM = 'access_key=' + FIXER_API_KEY
baseUrl = 'https://data.fixer.io/api/'


def get_ticker(base_currency):
	result = requests.get(
		baseUrl + 'latest?&{}&format=1&base={}&symbols=ZAR'.format(ACCESS_KEY_PARAM, base_currency.upper()))
	return result.json()


def get_tickers():
	result = requests.get(baseUrl + 'latest?&{}&format=1&base=ZAR&symbols=EUR,USD,GBP'.format(ACCESS_KEY_PARAM))
	return result.json()['rates']


@retry(Exception)
def get_historical_ticker(dt):
	date_string = dt.strftime('%Y-%m-%d')

	url = baseUrl + '{date_string}?{}&format=1&base=ZAR&symbols=EUR,USD,GBP,AUD'.format(
		ACCESS_KEY_PARAM,
		date_string=date_string)
	result = requests.get(url).json()
	return result['timestamp'], result['rates']
