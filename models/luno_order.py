from datetime import datetime

from models.order_base import OrderBase


class LunoOrder(OrderBase):

	def __init__(self, order_dict=None, zax=None, matched_zar=0):
		super().__init__(order_dict, zax, matched_zar)

	def populate(self, order_dict):
		self.id = order_dict.get('order_id')
		self.type = order_dict.get('type')
		self.state = order_dict.get('state')
		self.pair = order_dict.get('pair')

		self.limit_price = float(order_dict.get('limit_price', 0))
		self.limit_volume = float(order_dict.get('limit_volume', 0))

		self.zar = float(order_dict.get('zar', 0))
		self.fee_zar = float(order_dict.get('fee_zar', 0))

		self.btc = float(order_dict.get('btc', 0))
		self.fee_btc = float(order_dict.get('fee_btc', 0))

		if order_dict.get('creation_timestamp'):
			self.creation_timestamp = datetime.fromtimestamp(order_dict.get('creation_timestamp') / 1000)
			self.completed_timestamp = datetime.fromtimestamp(order_dict.get('completed_timestamp') / 1000)

		# If type is 'BID' negate values (for trade records)
		if self.type == 'BID':
			self.zar *= -1
			self.btc *= -1

	@property
	def is_unfilled(self):
		return self.state == 'PENDING' and self.btc == 0

	@property
	def is_partially_filled(self):
		return self.state == 'PENDING' and self.btc > 0

	@property
	def is_cancelled(self):
		return self.state == 'COMPLETE' and self.btc == 0

	@property
	def is_complete(self):
		return self.state == 'COMPLETE' and self.btc != 0
