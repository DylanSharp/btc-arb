import requests
from requests.auth import HTTPBasicAuth

from models.luno_order import LunoOrder
from utils.helpers import retry, APIError, UnauthorizedError, TooManyRequestsError, InsufficientFundsError
from misc.utils import log, wait, round_down
from settings import ACCOUNT_HOLDER, LUNO_ACCOUNT_CREDENTIALS, LUNO_BITCOIN_WITHDRAWAL_ADDRESS

base_url = 'https://api.mybitx.com/api/1'


class LunoIntegration:

	def __init__(self):
		self.name = 'luno'
		self.credentials = LUNO_ACCOUNT_CREDENTIALS
		self.receiving_address = LUNO_BITCOIN_WITHDRAWAL_ADDRESS

	def __repr__(self):
		return 'Luno Integration: {}'.format(ACCOUNT_HOLDER.title())

	def _get_auth(self):
		return HTTPBasicAuth(
			self.credentials.get('auth_user'),
			self.credentials.get('auth_secret'),
		)

	@retry(APIError)
	def get_balances(self):
		response = requests.get(base_url + '/balance', auth=self._get_auth())
		if response.status_code == 401:
			raise UnauthorizedError('Unauthorized. Check the API key permissions.')
		if response.status_code != 200 and getattr(response, 'text', None) is not None:
			raise APIError(response.text)
		output_dict = {b['asset']: float(b['balance']) for b in response.json()['balance']}
		output_dict['BTC'] = output_dict['XBT']
		return output_dict

	def get_transactions(self, account_id):
		response = requests.get(
			base_url + '/accounts/{}/transactions?min_row={}&max_row={}'.format(account_id, -100, 0),
			auth=self._get_auth())
		# TODO: Handle an error response here
		return response.json()

	@retry(Exception)
	def get_ticker(self):
		response = requests.get(base_url + '/ticker?pair=XBTZAR')
		return response.json()

	@retry(Exception)
	def get_tickers(self):
		result = requests.get(base_url + '/tickers')
		return result.json()['tickers']

	def get_address(self, address, asset='XBT', max_retries=50):
		attempts = 0
		while attempts <= max_retries:
			try:
				response = requests.get(
					base_url + '/funding_address?address={}&asset={}'.format(address, asset), auth=self._get_auth())
				if response.status_code == 401:
					raise UnauthorizedError
				if response.status_code != 200 and getattr(response, 'text', None) is not None:
					raise Exception(response.text)
				return response.json()

			except UnauthorizedError:
				log('Unauthorized. Check the API key permissions.', level='w')
				raise ValueError('Unauthorized. Check the Luno API key has not expired and has the required permissions.')

			except Exception as e:
				log(e)
				attempts += 1
				wait(0.5)

	@retry(Exception)
	def cancel_order(self, order_id):
		log('Attempting to cancel order {} BTC on Luno'.format(order_id))
		payload = {
			'order_id': order_id
		}
		response = requests.post(base_url + '/stoporder', auth=self._get_auth(), data=payload)

		if response.status_code == 401:
			raise Exception(response.content.decode('utf-8'))
		if response.status_code != 200 and getattr(response, 'text', None) is not None:
			raise Exception(response.text)

		res_json = response.json()
		if isinstance(res_json['success'], bool) and not res_json['success']:
			log('Unexpected response when canceling order.')
			raise Exception(response.text)

		return response.json(), response.status_code

	def verify_receive_address(self, address, asset='XBT'):
		log('Verifying Luno receiving address {}'.format(address))
		retrieved_address = self.get_address(address)
		try:
			address_valid = retrieved_address['address'] == address
			asset_valid = retrieved_address['asset'] == asset
			is_valid = address_valid and asset_valid
			log('Valid Luno receive address: {}'.format(is_valid))
			return is_valid
		except KeyError:
			return False

	def get_order(self, order_id, max_retries=50, return_dict=False):
		"""
		Attempts to get and return a Luno order.

		By default tries 50 times before giving up. Waits 0.5 seconds between attempts.

		:param order_id: the Luno assigned order id
		:param max_retries: number of times to retry if first attempt fails
		:param return_dict: if True returns a dict of the order else returns a LunoOrder.
		:return: dict or LunoOrder
		"""
		success = False
		attempts = 0
		while not success and attempts <= max_retries:
			try:
				response = requests.get(base_url + '/orders/' + order_id, auth=self._get_auth())

				if response.status_code == 401:
					raise Exception(response.content.decode('utf-8'))
				if response.status_code != 200 and getattr(response, 'text', None) is not None:
					raise Exception(response.text)

				success = True
				res_json = response.json()
				if return_dict:
					return res_json
				else:
					return LunoOrder(zax=self, order_dict=res_json)
			except Exception as e:
				log(e)
				attempts += 1
				wait(0.25)

		raise Exception('get_order() failed after {} attempts.'.format(attempts))

	def get_withdrawals(self):
		response = requests.get(base_url + '/withdrawals', auth=self._get_auth())

		if response.status_code == 401:
			raise Exception(response.content.decode('utf-8'))
		if response.status_code != 200 and getattr(response, 'text', None) is not None:
			raise Exception(response.text)

		return response.json()

	def cancel_withdrawal(self, withdrawal_id):
		response = requests.delete(base_url + '/withdrawals/{}'.format(withdrawal_id), auth=self._get_auth())

		if response.status_code == 401:
			raise Exception(response.content.decode('utf-8'))
		if response.status_code != 200 and getattr(response, 'text', None) is not None:
			raise Exception(response.text)

		return response.json()

	@retry(Exception)
	def get_orders(self):
		response = requests.get(base_url + '/listorders?limit=500', auth=self._get_auth())

		if response.status_code == 401:
			raise UnauthorizedError(response.content.decode('utf-8'))
		if response.status_code != 200 and getattr(response, 'text', None) is not None:
			raise Exception(response.text)

		res_json = response.json()
		return [LunoOrder(zax=self, order_dict=order) for order in res_json['orders']]

	@retry(Exception)
	def get_open_orders(self):
		orders = self.get_orders()
		return [o for o in orders if not o.is_cancelled and not o.is_complete]

	def get_orderbook(self, max_retries=50):
		attempts = 0
		while attempts <= max_retries:
			try:
				response = requests.get(base_url + '/orderbook?pair=XBTZAR', auth=self._get_auth())

				if response.status_code == 401:
					raise Exception(response.content.decode('utf-8'))
				if response.status_code != 200 and getattr(response, 'text', None) is not None:
					raise Exception(response.text)

				return response.json()
			except Exception as e:
				log(e)
				attempts += 1
				wait(0.1)

		raise Exception('get_orderbook() failed after {} attempts.'.format(attempts))

	@retry((TooManyRequestsError, InsufficientFundsError), total_tries=10)
	def limit_order(self, order_type, btc_amount, price, post_only=False):
		type_descr = ''
		if order_type == 'ASK':
			type_descr = 'ASK (sell)'
		elif order_type == 'BID':
			type_descr = 'BID (buy)'

		btc_amount = round_down(btc_amount, decimals=6)

		log('Creating {} of {} BTC on Luno @ R{}/BTC amounting to R{:.2f}'.format(
			type_descr, btc_amount, price, btc_amount * price)
		)
		payload = {
			'pair': 'XBTZAR',
			'type': order_type,
			'volume': '{}'.format(round_down(btc_amount, 6)),
			'price': round(price),
			'post_only': post_only,
		}
		response = requests.post(
			base_url + '/postorder',
			auth=self._get_auth(),
			data=payload
		)

		if response.status_code == 401:
			raise Exception(response.content.decode('utf-8'))
		if response.status_code == 429:
			# We want to retry if the error was unrelated to the order itself.
			raise TooManyRequestsError
		if response.status_code != 200 and getattr(response, 'text', None) is not None:
			if response.json()['error_code'] == 'ErrInsufficientBalance':
				raise InsufficientFundsError
			raise Exception(response.text)

		return response.json(), response.status_code

	def sell_limit_order(self, *args, **kwargs):
		order_type = 'ASK'
		return self.limit_order(order_type, *args, **kwargs)

	def buy_limit_order(self, *args, **kwargs):
		order_type = 'BID'
		return self.limit_order(order_type, *args, **kwargs)

	def get_order_ids_in_range(self, lower_bound, upper_bound):
		order_ids = []
		orders = self.get_orders()
		order_sum = 0
		for order in orders:
			if upper_bound >= order.creation_timestamp >= lower_bound and order.zar != 0:
				order_sum += order.zar
				print('{},{},{}'.format(order.id, order.creation_timestamp, order.zar))
				# print('\'{}\','.format(order.id))
				order_ids.append(order.id)
		print(order_sum)
		return order_ids


if __name__ == '__main__':
	integration = LunoIntegration()
	integration.get_order_ids_in_range()
