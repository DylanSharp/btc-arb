# - *- coding: utf- 8 - *-

import hashlib
import hmac
import time
from datetime import timedelta

from config.fee_config import BITSTAMP_DEPOSIT_LOSS, BITSTAMP_INSTANT_TRADE_LOSS, BITSTAMP_WITHDRAWAL_FEE
from utils.api_helpers import post_request, get_request
from utils.helpers import UnauthorizedError, retry
from models import bitstamp
from misc.utils import log, wait, byte_encode, spacer
from settings import BITSTAMP_ACCOUNT_CREDENTIALS, ACCOUNT_HOLDER

base_url = 'https://www.bitstamp.net/api/v2'

BITSTAMP_TRANSACTION_TYPES = {
	'deposit': 0,
	'withdrawal': 1,
	'market_trade': 2,
	'sub_account_transfer': 14
}


class BitstampIntegration:

	def __init__(self):
		self.credentials = BITSTAMP_ACCOUNT_CREDENTIALS
		self.encode_credentials()

		self.deposit_fee = BITSTAMP_DEPOSIT_LOSS
		self.taker_fee = BITSTAMP_INSTANT_TRADE_LOSS
		self.withdrawal_fee = BITSTAMP_WITHDRAWAL_FEE

	def __repr__(self):
		return 'Bitstamp Integration: {}'.format(ACCOUNT_HOLDER.title())

	@staticmethod
	def _get_nonce():
		return str(round(time.time() * 10000000))

	def _get_auth(self):
		nonce = self._get_nonce()
		message = str.encode(nonce) + self.credentials['CUSTOMER_ID'] + self.credentials['API_KEY']
		signature = hmac.new(
			self.credentials['API_SECRET'],
			msg=message,
			digestmod=hashlib.sha256
		).hexdigest().upper()

		return {
			'nonce': int(nonce),
			'key': self.credentials['API_KEY'],
			'signature': signature
		}

	def get_user_transactions(self, currency=None):
		payload = {
			'limit': '1000'
		}
		payload.update(self._get_auth())
		url = '{}/user_transactions/'.format(base_url)
		if currency:
			url += '{}/'.format(currency)
		result = post_request(url, data=payload)
		if result.status_code != 200:
			raise Exception(result.text)
		result_json = result.json()
		return [bitstamp.BitstampTransaction(txn_dict) for txn_dict in result_json]

	def get_user_transactions_by_date_and_type(self, transaction_type, start_date=None, end_date=None, currency=None):
		type_code = BITSTAMP_TRANSACTION_TYPES[transaction_type]
		if end_date:
			end_date += timedelta(days=1)
		# Loop over transactions to find the one(s) on chosen date
		txns = self.get_user_transactions(currency)
		output = []
		if start_date and end_date:
			log('Looking for transactions of type {} [{}] and between dates {} and {}'.format(
				transaction_type, type_code, start_date, end_date))
		if start_date and not end_date:
			log('Looking for transactions of type {} [{}] and after {}'.format(transaction_type, type_code, start_date))

		for txn in txns:
			if start_date and end_date:
				if int(txn.type) == type_code and txn.datetime >= start_date < end_date:
					output.append(txn)
			if start_date and not end_date:
				if int(txn.type) == type_code and txn.datetime >= start_date:
					output.append(txn)

		return output

	@retry(Exception)
	def get_balances(self):
		try:
			response = post_request('{}/balance/'.format(base_url), data=self._get_auth())
			if response.status_code in (401, 403):
				raise UnauthorizedError()
			elif response.status_code != 200:
				raise Exception(response.text)
			return response.json()

		except UnauthorizedError:
			log('Unauthorized. Check the API key permissions.', level='w')
			raise ValueError('Unauthorized. Check the Bitstamp API key has not expired and has the required permissions.')

	def get_order(self, order_id, max_retries=50):
		success = False
		attempts = 0
		while not success and attempts <= max_retries:
			try:
				payload = {'id': '{}'.format(order_id)}
				payload.update(self._get_auth())
				response = post_request('{}/order_status/'.format(base_url), data=payload).json()

				if response['status'] == 'error':
					raise Exception(response['reason'])

				# Todo: Find out why this always returns "Canceled" even though complete lately.
				elif response['status'] == 'Canceled':
					log('Order status "Canceled" but assuming it is complete.', level='w')
					pass
				elif response['status'] != 'Finished':
					raise Exception(
						'Order status not "Finished". Trying again. Current status: {}'.format(response.get('status')))

				return bitstamp.BitstampOrder(response)
			except Exception as e:
				log(e)
				attempts += 1
				wait(0.25)

		raise Exception('Failed after {} attempts.'.format(attempts))

	def instant_buy(self, fiat_amount, fiat_currency):
		fiat_amount_str = '{:.2f}'.format(fiat_amount)
		log('Attempting to purchase {} {} worth of BTC on Bitstamp.'.format(fiat_amount_str, fiat_currency.upper()))
		payload = {'amount': fiat_amount_str}
		payload.update(self._get_auth())
		response = post_request('{}/buy/instant/btc{}/'.format(base_url, fiat_currency), data=payload)

		if response.status_code != 200 and 'Order could not be placed' in str(response.json().get('reason')):
			log('Buy order failed with error: '.format(response.json().get('reason')))
			wait(1)
			return self.instant_buy(fiat_amount=fiat_amount, fiat_currency=fiat_currency)

		if response.status_code != 200:
			raise Exception(response.text)
		elif response.json().get('status') == 'error':
			raise Exception(str(response.json().get('reason')))

		bitstamp_order_id = response.json()['id']
		return self.get_order(bitstamp_order_id, max_retries=100)

	@staticmethod
	@retry(Exception)
	def get_ticker(pair):
		result = post_request('{}/ticker/{}/'.format(base_url, pair))
		ticker = result.json()
		ticker['pair'] = pair
		return ticker

	def get_tickers(self):
		result = get_request('{}/trading-pairs-info/'.format(base_url))
		pairs = [t['url_symbol'] for t in result.json()]
		tickers = []
		for pair in pairs:
			tickers.append(self.get_ticker(pair))
		return tickers

	@staticmethod
	def get_orderbook(fiat_currency):
		result = post_request('{}/order_book/btc{}/'.format(base_url, fiat_currency))
		return result.json()

	def withdraw_bitcoin(self, amount, address):
		log('Withdrawing {} BTC to {}'.format(amount, address))
		payload = {
			'amount': '{:.8f}'.format(amount),
			'address': address,
			'instant': 0
		}
		payload.update(self._get_auth())
		result = post_request('https://www.bitstamp.net/api/bitcoin_withdrawal/'.format(base_url), data=payload)
		result_json = result.json()
		if result_json.get('error'):
			raise Exception(result_json.get('error'))
		log('Withdrawal submitted for {} BTC to {}. Withdrawal ID:{}'.format(amount, address, result_json.get('id')))
		return result_json, result.status_code

	def get_withdrawal_requests(self):
		result = post_request('{}/withdrawal-requests/'.format(base_url), data=self._get_auth())
		result_json = result.json()
		return result_json

	def encode_credentials(self):
		key = self.credentials['API_KEY']
		secret = self.credentials['API_SECRET']
		customer_id = self.credentials['CUSTOMER_ID']

		self.credentials['API_KEY'] = byte_encode(key) if type(key) == str else key
		self.credentials['API_SECRET'] = byte_encode(secret) if type(secret) == str else secret
		self.credentials['CUSTOMER_ID'] = byte_encode(customer_id) if type(customer_id) == str else customer_id

	def get_order_ids_in_range(self, lower_bound, upper_bound):
		txns = self.get_user_transactions()
		txns.reverse()

		order_ids = []
		txn_count = 0
		txn_usd_sum = 0
		txn_btc_sum = 0

		for txn in txns:
			if lower_bound < txn.datetime < upper_bound and txn.order_id and txn.usd != 0 and txn.type == '2':
				txn_count += 1
				txn_btc_sum += txn.btc
				txn_usd_sum += txn.usd
				order_ids.append(txn.order_id)

		orders = []
		for i in set(order_ids):
			order = self.get_order(i)
			orders.append(order)

		order_txn_count = 0
		order_btc_sum = 0
		order_usd_sum = 0
		for order in orders:
			order_txn_count += len(order.transactions)
			order_btc_sum += order.total_bitcoin_bought
			order_usd_sum += order.total_fiat_spend
			print('\'{}\','.format(order.id))
			# print('\'{}\', {}, {}, {}, {}'.format(order.id, order.datetime, order.status, order.total_fiat_spend, order.total_bitcoin_bought))

			order_ids.append(order.id)
		print(spacer)
		print('txn_btc_sum', txn_btc_sum)
		print('txn_usd_sum', txn_usd_sum)
		print('txn_count', txn_count)
		return order_ids


if __name__ == '__main__':
	i = BitstampIntegration()
	ticker = i.get_ticker('btcusd')
	print(ticker)
