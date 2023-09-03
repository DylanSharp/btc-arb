import sys
import time

from integrations.bitstamp import BitstampIntegration
from misc.utils import log
from settings import ACCOUNT_HOLDER
from config.trade_config import trade_settings


def run(seconds_to_wait=180):
	bitstamp = BitstampIntegration()
	fiat_currency = trade_settings[ACCOUNT_HOLDER]['fiat_currency']

	starting_bitstamp_fiat_balance = float(bitstamp.get_balances()['{}_available'.format(fiat_currency)])
	log('Current {} Bitstamp Balance for {}: {}'.format(
		fiat_currency.upper(),
		ACCOUNT_HOLDER.capitalize(),
		starting_bitstamp_fiat_balance
	))

	# Loop until deposit comes in
	balance_unchanged = True
	while balance_unchanged:
		bitstamp_fiat_balance = float(bitstamp.get_balances()['{}_available'.format(fiat_currency)])
		balance_unchanged = bitstamp_fiat_balance <= starting_bitstamp_fiat_balance
		if balance_unchanged:
			log('{} balance unchanged, waiting another {} seconds before checking again ...'.format(
				fiat_currency.upper(), seconds_to_wait))
			time.sleep(seconds_to_wait)
		else:
			log('It looks like a deposit has come in for {}. {} balance now {}.'.format(
				ACCOUNT_HOLDER.capitalize(),
				fiat_currency.upper(),
				bitstamp_fiat_balance),
				notify=True
			)
			sys.exit()


if __name__ == '__main__':
	run()
