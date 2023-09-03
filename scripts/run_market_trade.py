import sys
import traceback

from models.market_trade import MarketTrade
from settings import ACCOUNT_HOLDER
from config.trade_config import trade_settings
from misc.utils import log, spacer

if __name__ == '__main__':
	trade = MarketTrade(**trade_settings)

	log(spacer)
	log('Market Order Trade', color='cyan')
	log('Trade Config:')
	log('# Account Holder: {} '.format(ACCOUNT_HOLDER.upper()))
	log('# Balances')
	log('### Bitstamp {} Balance: {}'.format(trade.fiat_currency.upper(), trade.bitstamp_fiat_balance))
	log('### Bitstamp BTC Balance: {}'.format(trade.bitstamp_btc_balance))
	log('### Luno BTC Balance: {}'.format(trade.luno_btc_balance))
	log('### Luno ZAR Balance: {}'.format(trade.luno_zar_balance))
	log(spacer)
	log('# Setup')
	log('### Profit in Bitcoin: {}'.format(trade_settings['profit_in_bitcoin']))
	log('### Target: {}%'.format(trade_settings['target']))
	log('### Total {} to sell: {}'.format(trade.fiat_currency.upper(), trade_settings['total_fiat_to_sell']))
	log('### Total ZAR to buy: {}'.format(trade_settings['total_zar_to_buy']) if trade_settings['total_zar_to_buy'] else 'NA')
	log('### {} Rate: {}'.format(trade.fiat_currency.upper(), trade_settings['fiat_rate'] or 'NA'))
	log('### Current profit: {}%'.format(trade.current_profit))
	log(spacer)

	if not trade_settings['profit_in_bitcoin']:
		log('Trades with profit in ZAR are not yet supported.', color='yellow')
		sys.exit(0)

	if not trade.balances_sufficient():
		sys.exit(0)

	if trade_settings['total_zar_to_buy'] > 0 and not trade_settings['profit_in_bitcoin']:
		log(
			'You have conflicting trade settings. If you want to take profit in ZAR, total_zar_to_buy must be 0 or None.',
			color='yellow'
		)
		sys.exit(0)

	if input('Are you sure you want to proceed? (Y/n)\n') != 'Y':
		sys.exit(0)

	try:
		trade.run()
	except Exception as e:
		log('Trade failed with exception:\n{}'.format(e), notify=True)
		traceback.print_exc()
