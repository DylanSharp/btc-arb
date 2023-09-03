import hashlib
import hmac
import json
import time

from config.fee_config import VALR_MAKER_FEE, VALR_TAKER_FEE, VALR_WITHDRAWAL_FEE
from misc.utils import log, round_down
from models.valr_order import ValrOrder
from settings import ACCOUNT_HOLDER, VALR_ACCOUNT_CREDENTIALS, VALR_MINIMUM_ORDER_SIZE, VALR_BITCOIN_WITHDRAWAL_ADDRESS
from utils.api_helpers import get_request, post_request, delete_request
from utils.helpers import retry

base_url = 'https://api.valr.com'

RECOGNIZED_CURRENCIES = ['ZAR', 'BTC']


class ValrIntegration:

	def __init__(self):
		self.name = 'valr'
		self.credentials = VALR_ACCOUNT_CREDENTIALS
		self.minimum_order_size = VALR_MINIMUM_ORDER_SIZE
		self.receiving_address = VALR_BITCOIN_WITHDRAWAL_ADDRESS

		self.maker_fee = VALR_MAKER_FEE
		self.taker_fee = VALR_TAKER_FEE
		self.withdrawal_fee = VALR_WITHDRAWAL_FEE

	def __repr__(self):
		return 'VALR Integration: {}'.format(ACCOUNT_HOLDER.title())

	def _get_auth_headers(self, verb, url, body=""):
		"""
		Returns the required auth headers for an authenticated request.

		:type verb: http verb
		:type url: full url
		:type body: http request body as a string
		"""
		path = url[20:]
		timestamp = int(time.time() * 1000)
		api_key_secret = self.credentials['secret']
		payload = "{}{}{}{}".format(timestamp, verb.upper(), path, body)
		message = bytearray(payload, 'utf-8')
		signature = hmac.new(bytearray(api_key_secret, 'utf-8'), message, digestmod=hashlib.sha512).hexdigest()
		return {
			'X-VALR-API-KEY': self.credentials['key'],
			'X-VALR-SIGNATURE': signature,
			'X-VALR-TIMESTAMP': bytes(str(timestamp), 'utf-8'),
		}

	# Public APIs

	@retry(Exception)
	def get_ticker(self, pair='BTCZAR'):
		response = get_request('{}/v1/public/{}/marketsummary'.format(base_url, pair))
		result = response.json()

		# Trade requires the response to be a similar shape to the other API responses.
		result['ask'] = result['askPrice']
		result['bid'] = result['bidPrice']
		return result

	@retry(Exception)
	def get_tickers(self):
		response = get_request('{}/v1/public/marketsummary'.format(base_url))
		return response.json()

	@retry(Exception)
	def get_orderbook_public(self, pair='BTCZAR'):
		response = get_request('{}/v1/public/{}/orderbook/full'.format(base_url, pair))
		return response.json()

	# Secure APIs

	@retry(Exception)
	def get_orderbook_full(self, pair='BTCZAR'):
		url = '{}/v1/marketdata/{}/orderbook'.format(base_url, pair)
		response = get_request(url, headers=self._get_auth_headers('GET', url))
		return response.json()

	@retry(Exception)
	def get_orderbook(self, pair='BTCZAR'):
		"""
		This returns an aggregated version of the book which is all we actually need.

		:param pair:
		:return:
		"""
		response = get_request('{}/v1/public/{}/orderbook'.format(base_url, pair))
		return response.json()

	@retry(Exception)
	def get_balances(self):
		url = '{}/v1/account/balances'.format(base_url)
		response = get_request(url, headers=self._get_auth_headers('GET', url))
		response_dict = {
			b['currency']: float(b['available']) for b in response.json()
			if b['currency'] in RECOGNIZED_CURRENCIES
		}
		return response_dict

	@retry(Exception)
	def get_transactions(self, offset=0, limit=100):
		url = '{}/v1/account/transactionhistory?skip={}&limit={}'.format(base_url, offset, limit)
		response = get_request(url, headers=self._get_auth_headers('GET', url))
		return response.json()

	@retry(Exception)
	def get_orders(self, offset=0, limit=100):
		"""
		This endpoint does NOT return open orders.
		"""
		url = '{}/v1/orders/history?skip={}&limit={}'.format(base_url, offset, limit)
		response = get_request(url, headers=self._get_auth_headers('GET', url))
		res_json = response.json()
		return [ValrOrder(order_dict=o, zax=self) for o in res_json]

	@retry(Exception)
	def get_open_orders(self, offset=0, limit=100):
		url = '{}/v1/orders/open'.format(base_url, offset, limit)
		response = get_request(url, headers=self._get_auth_headers('GET', url))
		res_json = response.json()
		return [ValrOrder(order_dict=o, zax=self) for o in res_json]

	def get_deposit_address(self, asset='BTC'):
		url = '{}/v1/wallet/crypto/{}/deposit/address'.format(base_url, asset)
		response = get_request(url, headers=self._get_auth_headers('GET', url))
		return response.json()

	def verify_receive_address(self, address, currency='BTC'):
		log('Verifying VALR receiving address {}'.format(address))
		retrieved_address = self.get_deposit_address()
		try:
			address_valid = retrieved_address['address'] == address
			currency_valid = retrieved_address['currency'] == currency
			is_valid = address_valid and currency_valid
			log('Valid VALR receive address: {}'.format(is_valid))
			return is_valid
		except KeyError:
			return False

	@retry(ValueError)
	def limit_order(self, order_type, btc_amount, price, post_only=True):
		side = ''
		if order_type.upper() == 'ASK':
			side = 'SELL'
		elif order_type.upper() == 'BID':
			side = 'BUY'

		btc_amount = round_down(btc_amount, decimals=6)
		order_value = btc_amount * price

		log('Creating {} order of {} BTC on VALR @ R{}/BTC amounting to R{:.2f}'.format(
			side, btc_amount, price, order_value)
		)
		url = '{}/v1/orders/limit'.format(base_url)
		payload = {
			'side': side,
			'quantity': '{}'.format(btc_amount),
			'price': round(price),
			'pair': 'BTCZAR',
			'postOnly': post_only
		}
		body = json.dumps(payload)
		response = post_request(
			url,
			headers=self._get_auth_headers('POST', url, body),
			data=body
		)

		res_json = response.json()
		if response.status_code != 202:
			raise ValueError(res_json)

		return res_json

	@retry(Exception)
	def get_order(self, order_id, pair='BTCZAR', return_dict=False):
		"""
		Attempts to get and return a VALR order.

		"""
		url = '{}/v1/orders/{}/orderid/{}'.format(base_url, pair, order_id)
		response = get_request(url, headers=self._get_auth_headers('GET', url))

		res_json = response.json()
		if return_dict:
			return res_json
		else:
			return ValrOrder(zax=self, order_dict=res_json)

	@retry(Exception)
	def cancel_order(self, order_id, pair='BTCZAR'):
		"""
		Attempts to cancel a VALR order.

		"""
		url = '{}/v1/orders/order'.format(base_url)
		payload = {
			'orderId': order_id,
			'pair': pair
		}
		body = json.dumps(payload)
		response = delete_request(
			url,
			headers=self._get_auth_headers('DELETE', url, body),
			data=body
		)
		if response.status_code != 200:
			raise ValueError('Cancel order did not return a successful response.')

		return True

	def buy_limit_order(self, *args, **kwargs):
		return self.limit_order('BID', *args, **kwargs)

	@retry(ValueError)
	def sell_limit_order(self, *args, **kwargs):
		"""
		Creates a limit order and then fetches it and returns the ValrOrder object.
		:return: An instance of ValrOrder. 
		"""""
		response = self.limit_order('ASK', *args, **kwargs)
		order_id = response['id']
		order = self.get_order(order_id)

		if order.state == 'Failed':
			raise ValueError(order.failed_reason)

		return order

	def get_order_ids_in_range(self, lower_bound, upper_bound):
		order_ids = []
		orders = self.get_orders()
		order_sum = 0
		for order in orders:
			if upper_bound >= order.creation_timestamp.replace(tzinfo=None) >= lower_bound and order.is_complete:
				order_sum += order.zar
				print('{},{},{}'.format(order.id, order.creation_timestamp, order.zar))
				print(order_sum)
				# print('\'{}\','.format(order.id))
				order_ids.append(order.id)
		print(order_sum)
		return order_ids


if __name__ == '__main__':
	integration = ValrIntegration()
	order = integration.sell_limit_order(btc_amount=0.0001, price=200000)
	order.cancel()
