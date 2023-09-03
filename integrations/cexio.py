import requests

base_url = 'https://cex.io/api/tickers'


def get_tickers():
	result = requests.get(base_url + '/BTC/USD/GBP/')
	return result.json()['data']


if __name__ == '__main__':

	tickers = get_tickers()
	print(tickers)
	# for key, value in tickers.items():
	# 	print(key, value['ticker']['buy'])
