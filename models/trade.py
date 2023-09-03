import sys
from datetime import datetime, timedelta

from models.trade_base import TradeBase
from settings import *
from write_to_sheets import write_trade_date_to_sheet
from misc.utils import log, wait, spacer


class LimitTrade(TradeBase):

	def __init__(self):
		super().__init__()
		self.fraction_remaining = 1
		self.not_yet_balanced = 0

		self.recent_buy_order_ids = []
		self.recent_buy_orders_fiat_spend = 0
		self.recent_buy_orders_btc = 0

	def run(self):
		while True:
			# Main outer trade loop.
			# A sell order gets placed once in this loop and then monitored in an inner loop.
			# When the life of that sell order is over (completed or cancelled),
			# this loop will restart but only if the total trade is not yet complete.

			restart_outer_loop = False

			self.recent_buy_order_ids = []
			self.recent_buy_orders_fiat_spend = 0
			self.recent_buy_orders_btc = 0

			self.log_state()

			# If there is not enough BTC in Zax, wait until there is.
			self.update_zax_balances()
			if self.zax_btc_balance < (self.zax.minimum_order_size + ZAX_ORDER_BUFFER):
				log(
					'BTC balance in {} is below the minimum order size, waiting '
					'for deposit to arrive before continuing trade.'.format(self.trade_settings['zax']))
				wait(2)
				continue

			self.update_current_profit()

			if not self.target_hit:
				log('Target not hit. Waiting a sec and trying again.')
				wait(1)
				continue

			# Create a sell limit order on zax at latest price and start monitoring (ensure it is post only).
			self.sell_order = self.zax.sell_limit_order(
				btc_amount=self.btc_to_sell, price=self.zax_bid_price + 1, post_only=True
			)

			while True:
				# Inner, secondary loop.
				# This is the loop that constantly checks the status of the sell order and
				# then routes the code execution accordingly.
				# The 3 main potential outcomes are:
				# 1. restart this inner loop and check again
				# 2. cancel the sell order and restart the outer loop
				# 3. break out of this loop and handle the state, usually the matching buy order

				log(spacer)
				log('Checking sell limit order state.')
				self.update_current_profit()
				self.sell_order.refresh()

				top_of_orderbook = self.zax_ask_price >= self.sell_order.limit_price

				# TARGET MISSED
				# Target is no longer being hit and order unfilled.
				if not self.target_hit and self.sell_order.is_unfilled:
					log('Target no longer hit and order unfilled. Cancelling order and starting over.')
					self.sell_order.cancel()
					restart_outer_loop = True
					break

				# Target is no longer being hit but order is partially filled.
				elif not self.target_hit and self.sell_order.is_partially_filled:
					log('Target no longer hit but order partially filled. Cancelling order and proceeding to BUY.')
					self.sell_order.cancel()
					break

				# TARGET HIT
				# Order is unfilled and is still on top, no need for more checks, check status again.
				elif self.sell_order.is_unfilled and top_of_orderbook:
					log('Order unfilled but is still on top of the book. Checking again.')
					wait(1)
					continue

				# Order is unfilled but no longer on top, cancel order and start again.
				elif self.sell_order.is_unfilled and not top_of_orderbook:
					log('Order unfilled but no longer at the top of the book. Canceling order and restarting trade.')
					self.sell_order.cancel()
					restart_outer_loop = True
					break

				# Partially filled but still on top, keep waiting for it to fill.
				elif self.sell_order.is_partially_filled and top_of_orderbook:
					log('Order partially filled but is still at top of the book.')
					log('{:.2f}% filled.'.format(self.sell_order.percentage_filled), as_art=True)
					log('{:.6f} unmatched ZAR'.format(self.sell_order.unmatched_zar))

					# If there is any actionable unmatched zar, attempt to match on Bitstamp.
					if self.has_actionable_unmatched_zar:
						self.attempt_to_match_unmatched_zar()
					else:
						log('No actionable unmatched ZAR.')
						wait(0.5)

					continue

				# Partially filled but not on top, stop trade short (cancel order) and move to buy step.
				elif self.sell_order.is_partially_filled and not top_of_orderbook:
					log('Order partially filled but no longer at the top of the book. Moving to buy.')
					self.sell_order.cancel()
					break

				# Order is canceled, move to buy step.
				elif self.sell_order.is_cancelled:
					log('Order appears to have been cancelled.')
					break

				# Order is complete, move to buy step.
				elif self.sell_order.is_complete:
					log('Sell order complete. Continuing to final matching for this sell order.')
					break

				else:
					# Shouldn't ever get here.
					self.sell_order.log_state()
					raise ValueError('Unexpected state reached.')

			if restart_outer_loop:
				continue

			self.sell_order.log_state()

			# Handle the buy order based on the state of the sell order.

			# Sell order was fully or partially filled, buy order required.
			if self.sell_order.is_complete or self.sell_order.is_partially_filled:

				# Update fraction remaining for the trade.
				fraction_just_sold = self.sell_order.zar / self.total_zar_to_buy

				log('Fraction of total trade remaining before: {}'.format(self.fraction_remaining))
				self.fraction_remaining -= fraction_just_sold
				log('Fraction of total trade just sold: {}'.format(fraction_just_sold))
				log('Fraction of total trade remaining now: {}'.format(self.fraction_remaining))

				# If there is still some unmatched ZAR, match it now.
				self.attempt_to_match_unmatched_zar()

				self.send_trade_update_sms()

				if self.rebalance_after:
					# Don't withdraw from Bitstamp until there is a substantial amount or trade is complete
					# because the withdrawal fee is fixed and becomes expensive.
					if (self.not_yet_balanced > self.minimum_btc_withdrawal_size) or self.trade_complete:
						self.rebalance_btc()
					else:
						log('Unbalanced BTC ({}) below minimum withdrawal size ({}). Skipping withdrawal.'.format(
							self.not_yet_balanced, self.minimum_btc_withdrawal_size))

			elif self.sell_order.is_cancelled:
				log(
					'Sell order was unexpectedly cancelled. If you did not do this, '
					'urgently check the state of the trade.', notify=True)
				sys.exit(0)

			# If the remaining amount is too small to sell, consider the trade complete.
			if self.trade_complete:
				log('Congratulations. Trade complete.', notify=True)
				self.update_trade_data_sheet()
				sys.exit(0)

	def attempt_to_match_unmatched_zar(self):
		log('Attempting to match {:.2f} unmatched ZAR from the current sell order.'.format(
			self.sell_order.unmatched_zar))

		if self.has_actionable_unmatched_zar:

			# Update account balances so that any matching done since the last check is accounted for in the balances.
			self.update_account_balances()

			# Sell the required amount of fiat on Bitstamp.
			log('### Performing buy order.')
			self.buy_order = self.bitstamp.instant_buy(
				fiat_amount=self.fiat_to_sell_to_match, fiat_currency=self.fiat_currency
			)
			self.buy_order.log_state()
			self.buy_order_ids.append(self.buy_order.id)

			# Update the matched amount on the sell_order.
			self.sell_order.matched_zar += self.sell_order.unmatched_zar

			# Update the unbalanced amount so this BTC gets withdrawn once sell_order cycle ends.
			self.not_yet_balanced += self.buy_order.total_bitcoin_bought

			# Update list of order ids.
			self.sell_order_ids.append(self.sell_order.id)

			self.recent_buy_order_ids.append(self.buy_order.id)
			self.recent_buy_orders_fiat_spend += self.buy_order.total_fiat_spend
			self.recent_buy_orders_btc += self.buy_order.total_bitcoin_bought

		else:
			log('Unmatched ZAR not actionable.')

	@property
	def trade_complete(self):
		return (
				self.total_btc_left_to_sell < (self.zax.minimum_order_size + ZAX_ORDER_BUFFER) or
				self.total_fiat_left_to_sell < BITSTAMP_MINIMUM_ORDER_SIZE
		)

	@property
	def minimum_btc_withdrawal_size(self):
		return MINIMUM_BTC_WITHDRAWAL_SIZE_IN_ZAR / self.zax_ask_price

	@property
	def fraction_complete(self):
		return 1 - self.fraction_remaining

	@property
	def max_btc_needed(self):
		return self.target_zar_from_sale / self.zax_ask_price

	@property
	def target_zar_from_sale(self):
		return self.fraction_remaining * self.total_zar_to_buy

	@property
	def total_fiat_left_to_sell(self):
		"""
		This value is only used to decide if the fraction remaining is so small that the trade should be ended early.
		:return: An estimate of the amount of fiat that will need to be sold if the sell order fills completely.
		"""
		return self.fraction_remaining * self.total_fiat_to_sell

	@property
	def total_btc_left_to_sell(self):
		"""
		This value is not intended to be used for the sell order but rather just to determine if the trade should
		be considered complete. i.e. if this value is smaller than the minimum order size.
		:return:
		"""
		return self.fraction_remaining * self.total_zar_to_buy / self.zax_ask_price

	@property
	def btc_to_sell(self):
		"""
		The amount of bitcoin to sell is considered at two levels. First, we consider how much of the overall trade
		remains and then, if this is more than is available, we just use the maximum available.

		We don't need to consider the minimum order size on zax because the trade should end if self.btc_to_sell
		is less than the minimum order size.

		WARNING: This conceals an api call in update_account_balances but it's critical that balances are up to date
		when this calculation is done.
		:return:
		"""
		self.update_account_balances()
		ideal_amount = self.fraction_remaining * self.total_zar_to_buy / self.zax_ask_price

		# To protect against from rounding errors and trying to sell less than is available,
		# subtract a very small safety buffer to leave in Bitcoin.
		available_zax_balance = self.zax_btc_balance - ZAX_ORDER_BUFFER

		if ideal_amount > available_zax_balance:
			return available_zax_balance
		else:
			return ideal_amount

	@property
	def has_actionable_unmatched_zar(self):
		"""
		Checks if there is any unmatched BTC that can be matched on Bitstamp. If there is, we can only buy on Bitstamp
		if the amount is large enough to exceed the minimum order size.
		:return:
		"""
		return (
				self.sell_order.unmatched_zar > 0 and
				self.fiat_to_sell_to_match > BITSTAMP_MINIMUM_ORDER_SIZE
		)

	@property
	def fiat_to_sell_to_match(self):
		"""
		The amount of fiat required to sell on Bitstamp to match the current unmatched amount in the open sell
		order on zax.
		:return:
		"""
		ideal_amount_to_sell = (self.sell_order.unmatched_zar / self.total_zar_to_buy) * self.total_fiat_to_sell

		# Todo: This logic below seems risky. Consider a better way.
		# Ensure we don't try sell more fiat than there is on Bitstamp.
		if ideal_amount_to_sell > self.bitstamp_fiat_balance:
			return self.bitstamp_fiat_balance
		else:
			return ideal_amount_to_sell

	def rebalance_btc(self):
		"""
		Send the bitcoin that was bought in the most recent order from Bitstamp to zax.

		It's not catastrophic if this fails for some reason but we log the outcome and send an sms.
		"""
		log('Balancing BTC by withdrawing from Bitstamp to {} ...'.format(self.trade_settings['zax']))
		try:
			# Double check the address we're sending to is valid on zax.
			assert (self.zax.verify_receive_address(self.zax.receiving_address))

			# Send BTC just bought from Bitstamp over to Zax less the withdrawal fee.
			self.bitstamp.withdraw_bitcoin(
				amount=self.not_yet_balanced - self.bitstamp.withdrawal_fee,
				address=self.zax.receiving_address
			)

			# If successful, reset unbalanced BTC
			self.not_yet_balanced = 0

		except AssertionError as e:
			log(
				'{} withdrawal address not found to be valid. Withdrawal not performed.'.format(
					self.trade_settings.za_echange.upper(), e),
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
		log('Percentage complete: {:.2f}%'.format(self.fraction_complete * 100), notify=True)
		log('Percentage remaining: {:.2f}%'.format(self.fraction_remaining * 100))

	def send_trade_update_sms(self):
		try:
			sms_txt = 'Trade update for {}:\n\n'.format(ACCOUNT_HOLDER.title())
			sms_txt += 'Just sold {:.6f} BTC for R{:.2f} and bought {:.6f} BTC for {:.2f} {}\n\n'.format(
				self.sell_order.btc,
				self.sell_order.zar,
				self.recent_buy_orders_btc,
				self.recent_buy_orders_fiat_spend,
				self.fiat_currency
			)
			btc_profit_for_partial_trade = self.recent_buy_orders_btc - self.sell_order.btc
			sms_txt += 'Profit in BTC: {:.6f} BTC\n'.format(btc_profit_for_partial_trade)
			sms_txt += 'Profit in ZAR: R{:.2f}\n'.format(btc_profit_for_partial_trade * self.zax_bid_price)
			sms_txt += 'Percentage complete: {:.2f}%\n'.format(self.fraction_complete * 100)
			sms_txt += 'Percentage remaining: {:.2f}%\n\n'.format(self.fraction_remaining * 100)
			sms_txt += 'Buy order ID(s): {}\n'.format(self.recent_buy_order_ids)
			sms_txt += 'Sell order ID: {}\n'.format(self.sell_order.id)
			log(sms_txt, notify=True)
		except Exception as e:
			log('Error sending trade update message, ignoring. {}'.format(e), level='w')

	def update_trade_data_sheet(self):
		# We don't care too much if this fails for some reason.
		try:
			kwargs = {
				'account_holder': ACCOUNT_HOLDER,
				'initial_rand_value': self.total_zar_to_buy,
				'fiat_bought': self.total_fiat_to_sell,
				'fiat_currency': self.fiat_currency,
				'fiat_rand_date': datetime.now() - timedelta(days=5),  # Allow 5 day window.
				'bitstamp_order_ids': self.buy_order_ids,
				'zax_order_ids': self.sell_order_ids
			}
			write_trade_date_to_sheet(**kwargs)
		except Exception as e:
			log('Something went wrong writing the trade data to google sheets:\n{}'.format(e))

	def get_loss_factor(self):
		return 1 - self.bitstamp.deposit_fee - self.bitstamp.taker_fee - self.zax.maker_fee
