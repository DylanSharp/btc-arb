import sys
from datetime import datetime, timedelta

from models.trade_base import TradeBase
from settings import *
from write_to_sheets import write_trade_date_to_sheet
from misc.utils import log, wait, spacer


class MarketTrade(TradeBase):

	def run(self):
		while True:
			# Main outer trade loop.
			# This loop monitors the profit margin and only continue to buy and sell if:
			# - the target is hit
			# - the required balances are available
			# - their is enough liquidity on the Luno order book
			# - their is enough liquidity on the Bitstamp order book

			log(spacer)
			self.update_current_profit()

			if not self.target_hit:
				wait_time = round((self.target - self.current_profit) * 2, 1)
				log('Target not hit. Waiting {} seconds and trying again.'.format(wait_time))
				wait(wait_time)
				continue

			log('Target hit. Checking balances.')

			# Check balances and don't proceed if balances insufficient.
			if not self.balances_sufficient():
				sys.exit(0)

			# Check liquidity and start again if liquidity insufficient.
			log('Balances good. Checking liquidity')
			if not self.enough_luno_liquidity():
				log('Not enough liquidity, trying again.', color='yellow')
				wait(0.5)
				continue

			# todo - check liquidity on Bitstamp (ASK side)

			# Create a sell limit order (ASK) on Luno at a price much lower than the highest BID so
			# that it is sold instantly.
			target_price = self.luno_bid_price * 0.9
			response, sell_order_status_code = self.luno.sell_limit_order(
				btc_amount=self.btc_to_sell, price=target_price
			)
			luno_order_id = response['order_id']
			self.sell_order = self.luno.get_order(luno_order_id)
			self.sell_order.log_state()

			while True:
				# Inner, secondary loop.
				# This loop checks the status of the sell order until it is complete.
				# The 3 main potential outcomes are:
				# 1. order not complete so restart this inner loop and check again
				# 2. if order is cancelled or in an unknown state exits the trade
				# 3. order is complete so break out of this loop and continue to the buy order

				log('Checking sell order state.')

				if self.sell_order.is_unfilled:
					log('Order unfilled. Checking again.')
					self.sell_order.refresh()
					continue

				elif self.sell_order.is_partially_filled:
					log('Order partially filled. Checking again.')
					self.sell_order.refresh()
					continue

				elif self.sell_order.is_cancelled:
					raise ValueError('Buy order appears to have been cancelled.')

				elif self.sell_order.is_complete:
					log('Order complete. Continuing to BUY order.')
					break

				else:
					# Shouldn't ever get here.
					raise ValueError('Unexpected state found for sell order.')

			# Handle the buy order.
			total_fiat_to_sell = self.total_fiat_to_sell

			# The minimum buy order on Bitstamp is 25 fiat so if the amount is less than 25 fiat we round up to 25.
			if total_fiat_to_sell < 25:
				total_fiat_to_sell = 25

			self.buy_order = self.bitstamp.instant_buy(fiat_amount=total_fiat_to_sell, fiat_currency=self.fiat_currency)
			self.buy_order.log_state()

			if not self.buy_order.complete:
				raise ValueError('Buy order not completed successfully.')

			self.send_trade_update_sms()

			if self.rebalance_after:
				log('Re-balancing BTC ...')
				self.rebalance_buy_order()

			# Update list of order ids
			self.sell_order_ids.append(self.sell_order.id)
			self.buy_order_ids.append(self.buy_order.id)

			self.update_trade_data_sheet()

			sys.exit()

	@property
	def enough_fiat(self):
		return self.total_fiat_to_sell <= self.bitstamp_fiat_balance

	@property
	def enough_btc(self):
		return self.btc_required <= self.luno_btc_balance

	@property
	def btc_required(self):
		# Add on a 2.5% factor as buffer.
		return self.btc_to_sell * 1.025

	@property
	def btc_to_sell(self):
		return self.total_zar_to_buy / self.luno_ask_price

	def balances_sufficient(self):
		log('Checking balances.')

		if not self.enough_fiat:
			log('Not enough {} in Bitstamp to attempt trade.'.format(self.fiat_currency.upper()))
		if not self.enough_btc:
			log('Not enough BTC in Luno to attempt trade.')

		return self.enough_btc and self.enough_fiat

	def rebalance_buy_order(self):
		"""
		Send the bitcoin that was bought in the most recent order from Bitstamp to luno.

		It's not catastrophic if this fails for some reason but we log the outcome and send an sms.
		"""
		try:
			# Double check the address we're sending to is valid on Luno.
			assert (self.luno.verify_receive_address(LUNO_BITCOIN_WITHDRAWAL_ADDRESS))

			# Send BTC just bought from Bitstamp over to Luno minus the withdrawal fee.
			self.bitstamp.withdraw_bitcoin(
				amount=self.buy_order.total_bitcoin_bought - BITSTAMP_WITHDRAWAL_FEE,
				address=LUNO_BITCOIN_WITHDRAWAL_ADDRESS
			)
		except AssertionError as e:
			log(
				'Luno withdrawal address not found to be valid. Withdrawal not performed.'.format(e),
				level='w',
				notify=True
			)
		except Exception as e:
			log(
				'Something went wrong withdrawing the BTC for the most recent order:\n{}'.format(e),
				level='w',
				notify=True
			)

	def log_state(self):
		log('Trade:')
		log('ID: {}'.format(self.sell_order.id))
		log('Type: {}'.format(self.sell_order.type))
		log('State: {}'.format(self.sell_order.state))
		log('Pair: {}'.format(self.sell_order.pair))

		log('Limit price: {}'.format(self.sell_order.limit_price))
		log('Limit volume: {}'.format(self.sell_order.limit_volume))

		log('Base: {}'.format(self.sell_order.base))
		log('Fee base: {}'.format(self.sell_order.fee_base))

		log('Counter: {}'.format(self.sell_order.counter))
		log('Fee counter: {}'.format(self.sell_order.fee_counter))

		log('Zar: {}'.format(self.sell_order.zar))
		log('Fee zar: {}'.format(self.sell_order.fee_zar))

		log('Btc: {}'.format(self.sell_order.btc))
		log('Fee btc: {}'.format(self.sell_order.fee_btc))

	def send_trade_update_sms(self):
		try:
			sms_txt = 'Congratulations. Trade complete.\n\n'
			sms_txt += 'Sold {:.6f} BTC for R{:.2f} and bought {:.6f} BTC for {:.2f} {}\n\n'.format(
				self.sell_order.btc,
				self.sell_order.zar,
				self.buy_order.total_bitcoin_bought,
				self.buy_order.total_fiat_spend,
				self.fiat_currency
			)
			sms_txt += 'Buy order ID: {}\n'.format(self.buy_order.id)
			sms_txt += 'Sell order ID: {}\n'.format(self.sell_order.id)
			log(sms_txt, notify=True)
		except Exception as e:
			log('Error sending trade update message, ignoring. {}'.format(e), level='w')

	def update_trade_data_sheet(self):
		# We don't care too much if this fails for some reason.
		try:
			kwargs = {
				'account_holder': self.account_holder,
				'initial_rand_value': self.total_zar_to_buy,
				'fiat_bought': self.total_fiat_to_sell,
				'fiat_currency': self.fiat_currency,
				'fiat_rand_date': datetime.now() - timedelta(days=5),  # Allow 5 day window.
				'bitstamp_order_ids': self.buy_order_ids,
				'luno_order_ids': self.sell_order_ids
			}
			write_trade_date_to_sheet(**kwargs)
		except Exception as e:
			log('Something went wrong writing the trade data to google sheets:\n{}'.format(e))

	def enough_luno_liquidity(self):
		"""
		Gets the Luno order book and steps through it working out the weighted average price and volume at each level.
		Returns when either the allowable slippage is already exceeded or the volume is met with sufficient liquidity.
		:return: Boolean pass or fail
		"""

		allowable_slippage = self.current_profit - self.target
		log('Allowable slippage: {}%'.format(allowable_slippage))

		orderbook = self.luno.get_orderbook()
		volume_total = 0
		product_total = 0

		for i, bid in enumerate(orderbook['bids']):
			price = float(bid['price'])
			volume = float(bid['volume'])

			volume_total += volume
			product_total += (price * volume)
			weighted_price = product_total / volume_total
			slippage = (1 - (weighted_price / self.luno_bid_price))

			log(
				'{}. Volume of {} BTC at weighted average price of R{} which would result in slippage of {:.6f}%.'
					.format(i + 1, volume_total, weighted_price, round(slippage * 100, 2))
			)

			# If at this point there is enough volume, check the weighted price
			if volume_total >= self.btc_required:
				# Return True if slippage is within limits
				return slippage <= allowable_slippage

			# If slippage is already exceeded at this point then return False
			if slippage > allowable_slippage:
				return False

		# We'd only get here if there was not enough liquidity in the whole orderbook which is practically impossible
		return False

	@staticmethod
	def get_loss_factor():
		return 1 - BITSTAMP_DEPOSIT_LOSS - BITSTAMP_INSTANT_TRADE_LOSS - LUNO_MARKET_ORDER_FEE
