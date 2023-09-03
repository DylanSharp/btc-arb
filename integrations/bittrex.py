import requests

base_url = 'https://api.bittrex.com/api/v1.1/public'


def get_tickers():
	result = requests.get(base_url + '/getmarketsummaries')
	return result.json()['result']


if __name__ == '__main__':

	tickers = get_tickers()['result']
	for i, ticker in enumerate(tickers):
		print(ticker['MarketName'], ticker['Ask'])
