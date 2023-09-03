import requests

base_url = 'https://www.ovex.io/api/v2'


def get_tickers():
	result = requests.get(base_url + '/tickers').json()
	pairs = []
	for k, v in result.items():
		pairs.append((k, v['ticker']['sell']))
	return pairs


if __name__ == '__main__':

	tickers = get_tickers()
	for key, value in tickers.items():
		print(key, value['ticker']['buy'])
