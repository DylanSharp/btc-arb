from integrations.bitstamp import BitstampIntegration
from integrations.helpers import get_zax_integration

from misc.utils import log
from settings import ACCOUNT_HOLDER
from config.trade_config import trade_settings


def run():
	zax_integration = get_zax_integration()
	bitstamp_integration = BitstampIntegration()

	zax_balances = zax_integration.get_balances()
	bitstamp_balances = bitstamp_integration.get_balances()

	zax_btc_balance = zax_balances['BTC']
	zax_zar_balance = zax_balances['ZAR']
	log('### Zax BTC balance: {:,}'.format(zax_btc_balance))
	log('### Zax ZAR balance: {:,}'.format(zax_zar_balance))

	bitstamp_btc_balance = float(bitstamp_balances['btc_available'])
	bitstamp_fiat_balance = float(bitstamp_balances['{}_available'.format(
		trade_settings[ACCOUNT_HOLDER]['fiat_currency'].lower()
	)])
	log('### Bitstamp BTC balance: {:,}'.format(bitstamp_btc_balance))
	log('### Bitstamp {} balance: {:,}'.format(
		trade_settings[ACCOUNT_HOLDER]['fiat_currency'].upper(),
		bitstamp_fiat_balance)
	)


if __name__ == '__main__':
	run()
