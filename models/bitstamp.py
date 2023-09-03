from dateutil import parser

from misc.utils import log


class BitstampTransaction:
	def __init__(self, txn_dict=None):
		if not txn_dict:
			txn_dict = {}
		self.id = txn_dict.get('id')
		self.order_id = txn_dict.get('order_id')
		self.datetime = parser.parse(txn_dict.get('datetime')[:10]) if txn_dict.get('datetime') is not None else None
		self.type = txn_dict.get('type')
		self.price = float(txn_dict.get('price') or 0)
		self.fee = float(txn_dict.get('fee') or 0)

		self.btc = float(txn_dict.get('btc') or 0)

		self.usd = float(txn_dict.get('usd') or 0)
		self.btc_usd = float(txn_dict.get('btc_usd') or 0)

		self.btc_eur = float(txn_dict.get('btc_eur') or 0)
		self.eur = float(txn_dict.get('eur') or 0)

		self.btc_fiat = self.btc_eur or self.btc_usd
		self.fiat = self.eur or self.usd


class BitstampOrder:
	def __init__(self, order_dict=None):
		if not order_dict:
			order_dict = {}
		self.id = order_dict.get('id')
		self.status = order_dict.get('status')
		self.transactions = [BitstampTransaction(txn_dict) for txn_dict in order_dict.get('transactions', [])]
		self.fees = 0
		self.total_bitcoin_bought = 0
		self.total_fiat_spend = 0
		self.weighted_average_price = 0
		self.datetime = None

		if self.transactions:
			self.datetime = self.transactions[0].datetime
			self.amalgamate_transactions()

	def amalgamate_transactions(self):
		total_bitcoin_bought = 0
		total_fiat_spend = 0
		total_fees = 0
		weighted_average_price = 0

		for txn in self.transactions:
			total_bitcoin_bought += txn.btc
			total_fees += txn.fee
			total_fiat_spend += txn.fiat

		if total_bitcoin_bought:
			weighted_average_price = abs(total_fiat_spend / total_bitcoin_bought)

		self.fees = total_fees
		self.total_bitcoin_bought = total_bitcoin_bought
		self.total_fiat_spend = total_fiat_spend
		self.weighted_average_price = weighted_average_price

	@property
	def complete(self):
		# Todo: Find out why this always returns "Canceled" even though complete lately.
		return self.status == 'Finished' or 'Canceled'

	def log_state(self):
		log('Buy order state:')
		log('ID: {}'.format(self.id))
		log('Status: {}'.format(self.status))

	@staticmethod
	def combine_orders(orders):
		combined_order = BitstampOrder()
		for order in orders:
			combined_order.datetime = order.datetime
			combined_order.fees += order.fees
			if getattr(order, 'transactions'):
				combined_order.transactions += order.transactions

		combined_order.amalgamate_transactions()

		return combined_order


def combine_transactions(transactions):
	combined_transaction = BitstampTransaction()
	for transaction in transactions:
		combined_transaction.datetime = transaction.datetime
		combined_transaction.fee += transaction.fee
		combined_transaction.usd += transaction.usd
		combined_transaction.btc += transaction.btc
		combined_transaction.btc_fiat += transaction.btc_fiat
		combined_transaction.fiat += transaction.fiat

	return combined_transaction
