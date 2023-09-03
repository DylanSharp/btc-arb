import sys
import traceback

from models.trade import LimitTrade
from misc.utils import log, spacer
from settings import ACCOUNT_HOLDER


def run():
	trade = LimitTrade()

	log(spacer)
	log('Limit Order Trade', color='cyan')
	log('Running with config:')
	log('# Account Holder: {} '.format(ACCOUNT_HOLDER.upper()))
	log('# Balances')
	log('### Bitstamp {} Balance: {}'.format(trade.fiat_currency.upper(), trade.bitstamp_fiat_balance))
	log('### Bitstamp BTC Balance: {}'.format(trade.bitstamp_btc_balance))
	log('### Luno BTC Balance: {}'.format(trade.zax_btc_balance))
	log('### Luno ZAR Balance: {}'.format(trade.zax_zar_balance))
	log(spacer)
	log('# Setup')
	log('### Target: {}%'.format(trade.trade_settings['target']))
	log('### Total {} to sell: {}'.format(trade.fiat_currency.upper(), trade.trade_settings['total_fiat_to_sell']))
	log('### Total ZAR to buy: {}'.format(trade.trade_settings['total_zar_to_buy']))
	log('### {} Rate: {}'.format(trade.fiat_currency.upper(), trade.trade_settings['fiat_rate'] or 'NA'))
	log('### Current profit: {}%'.format(trade.current_profit))
	log(spacer)

	if input('Are you sure you want to proceed? (Y/n)\n') != 'Y':
		sys.exit(0)

	try:
		trade.run()
	except Exception as e:
		log('Trade failed with exception:\n{}'.format(e), notify=True)
		traceback.print_exc()


if __name__ == '__main__':
	run()
