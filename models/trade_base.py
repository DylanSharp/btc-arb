import sys

from integrations import bitstamp, fixer, luno, valr
from settings import ACCOUNT_HOLDER
from config.trade_config import trade_settings
from misc.utils import log, spacer, print_art

VALID_FIAT_CURRENCIES = ('usd', 'eur')


class TradeBase:

	def __init__(self):
		self.trade_settings = trade_settings[ACCOUNT_HOLDER]

		self.bitstamp = bitstamp.BitstampIntegration()

		self.zax = None
		if self.trade_settings['zax'].lower() == 'luno':
			self.zax = luno.LunoIntegration()
		elif self.trade_settings['zax'].lower() == 'valr':
			self.zax = valr.ValrIntegration()

		self.target = self.trade_settings.get('target')
		self.target_in_zar = self.trade_settings.get('target_in_zar')
		self.rebalance_after = self.trade_settings.get('rebalance_after')
		self.total_fiat_to_sell = self.trade_settings.get('total_fiat_to_sell')
		self.total_zar_to_buy = self.trade_settings.get('total_zar_to_buy')
		self.fiat_currency = self.trade_settings.get('fiat_currency')
		self.fiat_rate = self.trade_settings.get('fiat_rate')

		self.current_profit = None
		self.potential_total_zar_out = None
		self.fiat_price = None
		self.bitstamp_ask_price = None
		self.bitstamp_bid_price = None
		self.zax_ask_price = None
		self.zax_bid_price = None

		self.target_hit = False

		self.bitstamp_btc_balance = None
		self.bitstamp_fiat_balance = None
		self.zax_btc_balance = None
		self.zax_zar_balance = None

		self.sell_order = None
		self.buy_order = None

		self.buy_order_ids = []
		self.sell_order_ids = []

		# Get and set all account balances and market data
		self.loss_factor = self.get_loss_factor()
		self.fiat_symbol = self.get_fiat_symbol()
		self.check_config()
		self.update_account_balances()
		self.check_fiat_balance()
		self.update_current_profit()

	def refresh_market_data(self):
		log('### Market data:')

		self.fiat_price = self.fiat_rate or fixer.get_ticker(self.fiat_currency.upper())['rates']['ZAR']
		log('### {} price: R{:,}'.format(self.fiat_currency.upper(), self.fiat_price))

		bitstamp_ticker = self.bitstamp.get_ticker('btc{}'.format(self.fiat_currency))
		self.bitstamp_bid_price = float(bitstamp_ticker['bid'])
		log('### Bitcoin price (Bid): {}{:,}'.format(self.fiat_symbol, self.bitstamp_bid_price))

		self.bitstamp_ask_price = float(bitstamp_ticker['ask'])
		log('### Bitcoin price (Ask): {}{:,}'.format(self.fiat_symbol, self.bitstamp_ask_price))

		zax_ticker = self.zax.get_ticker()
		self.zax_ask_price = float(zax_ticker['ask'])
		log('### Rand price (Ask): R{:,}'.format(self.zax_ask_price))

		self.zax_bid_price = float(zax_ticker['bid'])
		log('### Rand price (Bid): R{:,}'.format(self.zax_bid_price))
		log(spacer)

	def update_current_profit(self):
		self.refresh_market_data()

		self.potential_total_zar_out = round(
			self.total_fiat_to_sell / self.bitstamp_ask_price * (self.zax_bid_price + 1) * self.loss_factor, 2
		)
		self.current_profit = round(
			((1 / self.fiat_price / self.bitstamp_ask_price * (self.zax_bid_price + 1) * self.loss_factor) - 1) * 100,
			2
		)

		if self.target_in_zar:
			self.target_hit = self.potential_total_zar_out >= self.total_zar_to_buy
			log('### Target ZAR: {:,}'.format(self.total_zar_to_buy))
			log('### Current potential ZAR: {:,}'.format(self.potential_total_zar_out))

			if self.target_hit:
				color = 'cyan'
				print_art('R{:,}'.format(self.potential_total_zar_out), color=color)
				log('### Target hit.', color=color)
			else:
				color = 'yellow'
				print_art('R{:,}'.format(self.potential_total_zar_out), color=color)
				log('### Target not hit.', color=color)
		else:
			self.target_hit = self.current_profit >= self.target
			log('### Target profit: {}%'.format(self.target))
			log('### Current profit: {}%'.format(self.current_profit))

			if self.target_hit:
				color = 'cyan'
				print_art('{} %'.format(self.current_profit), color=color)
				log('### Target hit.', color=color)
			else:
				color = 'yellow'
				print_art('{} %'.format(self.current_profit), color=color)
				log('### Target not hit.', color=color)

	def update_zax_balances(self):
		zax_balances = self.zax.get_balances()
		self.zax_btc_balance = zax_balances['BTC']
		self.zax_zar_balance = zax_balances['ZAR']
		log('### {} BTC balance: {:,}'.format(self.trade_settings['zax'].upper(), self.zax_btc_balance))
		log('### {} ZAR balance: {:,}'.format(self.trade_settings['zax'].upper(), self.zax_zar_balance))

	def update_bitstamp_balances(self):
		bitstamp_balances = self.bitstamp.get_balances()
		self.bitstamp_btc_balance = float(bitstamp_balances['btc_available'])
		self.bitstamp_fiat_balance = float(bitstamp_balances['{}_available'.format(self.fiat_currency)])
		log('### Bitstamp BTC balance: {:,}'.format(self.bitstamp_btc_balance))
		log('### Bitstamp EUR balance: {:,}'.format(self.bitstamp_fiat_balance))

	def update_account_balances(self):
		log('### Updating all account balances.')
		self.update_zax_balances()
		self.update_bitstamp_balances()

	def get_fiat_symbol(self):
		if self.fiat_currency == 'usd':
			return '$'
		if self.fiat_currency == 'eur':
			return '€'
		else:
			return 'X'

	def sanity_check_rates(self):
		calculated_rate = self.total_zar_to_buy / self.total_fiat_to_sell
		lower_bound = self.fiat_rate * 0.95
		upper_bound = self.fiat_rate * 1.05
		percentage_different = (self.fiat_rate - calculated_rate) / self.fiat_rate * 100
		sane = lower_bound < calculated_rate < upper_bound

		if not sane:
			log(
				'The fiat rate you have configured is very different ({:.2f}%) from the calculated rate.'.format(
					percentage_different), color='yellow'
			)
			if input(
					'Are you sure it is correct?\n'
					'Calculated rate: {:.3f}\n'
					'Configured rate: {}\n'
					'(Y/n)\n'.format(
						calculated_rate,
						self.fiat_rate)) != 'Y':
				sys.exit(0)

	def check_config(self):
		# Sanity check rates unless target is denominated in ZAR.
		if not self.target_in_zar:
			self.sanity_check_rates()

		if self.fiat_currency not in VALID_FIAT_CURRENCIES:
			log('"{}" is not a valid fiat currency. Options are {}.'.format(self.fiat_currency, VALID_FIAT_CURRENCIES))
			sys.exit(0)

	def check_fiat_balance(self):
		if self.total_fiat_to_sell > self.bitstamp_fiat_balance:
			log(
				'{fiat_currency} balance too low.\n'
				'The {fiat_currency} balance in Bitstamp is {:,} '
				'and you are trying to sell {:,}.'.format(
					self.bitstamp_fiat_balance, self.total_fiat_to_sell, fiat_currency=self.fiat_currency.upper()),
				color='yellow'
			)
			sys.exit(0)

	@staticmethod
	def get_loss_factor():
		raise ValueError('get_loss_factor must be overridden by child class.')


if __name__ == '__main__':
	pass
