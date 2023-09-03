import requests

base_url = 'https://api.binance.com'


def get_tickers(je=False):
	url = base_url
	if je:
		url = 'https://api.binance.je'

	result = requests.get(url + '/api/v3/ticker/price')
	return result.json()


if __name__ == '__main__':

	tickers = get_tickers()
	for ticker in tickers:
		print(ticker['symbol'])
