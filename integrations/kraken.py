import requests

base_url = 'https://api.kraken.com/0'


def get_pairs():
	result = requests.get(base_url + '/public/AssetPairs')
	return [k for k in result.json()['result'].keys()]


def get_tickers():
	pair_names = get_pairs()
	pairs = []
	for pair in pair_names:
		result = requests.get(base_url + '/public/Ticker?pair={}'.format(pair)).json()['result']
		try:
			result = result[pair]
			pairs.append({
				'pair': pair,
				'ask': result['a'][0],
				'bid': result['b'][0]
			})
		except KeyError:
			print('Didn\'t find {} in the results. Skipping pair.'.format(pair))
	return pairs


if __name__ == '__main__':
	tickers = get_tickers()