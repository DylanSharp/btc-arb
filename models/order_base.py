from misc.utils import log


class OrderBase:

	def __init__(self, order_dict=None, zax=None, matched_zar=0):

		if not order_dict:
			order_dict = {}

		self.zax = zax or self.zax
		self.matched_zar = matched_zar

		self.id = None
		self.type = None
		self.state = None
		self.pair = None

		self.limit_price = None
		self.limit_volume = None

		self.zar = None
		self.fee_zar = None

		self.btc = None
		self.fee_btc = None

		self.creation_timestamp = None
		self.completed_timestamp = None

		if order_dict:
			self.populate(order_dict=order_dict)

	def populate(self, order_dict):
		"""
		Populates all properties from the dict returned from the exchange.
		"""
		raise ValueError('Child must override this method. Unique to each exchange.')

	@property
	def is_unfilled(self):
		raise ValueError('Child must override this method. Unique to each exchange.')

	@property
	def is_partially_filled(self):
		raise ValueError('Child must override this method. Unique to each exchange.')

	@property
	def is_cancelled(self):
		raise ValueError('Child must override this method. Unique to each exchange.')

	@property
	def is_complete(self):
		raise ValueError('Child must override this method. Unique to each exchange.')

	@property
	def potential_zar(self):
		return self.limit_volume * self.limit_price

	@property
	def percentage_filled(self):
		return (self.btc / self.limit_volume) * 100 if not self.is_cancelled else None

	@property
	def unmatched_zar(self):
		return self.zar - self.matched_zar

	@property
	def weighted_average_price(self):
		return self.zar / self.btc if self.btc else None

	def cancel(self):
		response = self.zax.cancel_order(self.id)
		self.refresh()
		self.log_state()
		return response

	def refresh(self):
		"""
		Re-fetch the order from zax and update its state.
		"""
		log('Refreshing order {}'.format(self.id))
		self.__init__(self.zax.get_order(self.id, return_dict=True), matched_zar=self.matched_zar)

	def log_state(self):
		log('Sell order state:')
		log('ID: {}'.format(self.id))
		log('State: {}'.format(self.state))
		log('Cancelled: {}'.format(self.is_cancelled))
		log('ZAR: {}'.format(self.zar))
		log('BTC: {}'.format(self.btc))
		log('Fee BTC: {}'.format(self.fee_btc))
		log('Fee ZAR: {}'.format(self.fee_zar))
		log('Price: {}'.format(self.limit_price))
		log('Volume: {}'.format(self.limit_volume))
		log('Potential ZAR: {}'.format(self.potential_zar))
		log('Percentage filled: {} %'.format(self.percentage_filled))
		log('Unmatched ZAR: {}'.format(self.unmatched_zar))
		log('Matched ZAR: {}'.format(self.matched_zar))

	def combine_orders(self, orders):
		c_order = self.__class__(zax=orders[0].zax)
		c_order.fee_btc = 0
		c_order.fee_zar = 0
		c_order.btc = 0
		c_order.zar = 0

		c_order.creation_timestamp = orders[0].creation_timestamp
		c_order.completed_timestamp = orders[0].completed_timestamp

		for order in orders:
			c_order.fee_btc += order.fee_btc
			c_order.fee_zar += order.fee_zar
			c_order.btc += order.btc
			c_order.zar += order.zar

		return c_order
