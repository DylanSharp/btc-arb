import sys

from integrations.bitstamp import BitstampIntegration
from integrations.helpers import get_zax_integration
from integrations.luno import LunoIntegration
from integrations.valr import ValrIntegration
from settings import BITSTAMP_WITHDRAWAL_FEE, ACCOUNT_HOLDER
from misc.utils import log, spacer


def run():
	bitstamp = BitstampIntegration()
	bitstamp_balances = bitstamp.get_balances()
	bitstamp_btc_balance = float(bitstamp_balances['btc_available'])

	log(spacer)
	log('Withdraw BTC', color='cyan')
	log('Config:')
	log('# Account Holder: {} '.format(ACCOUNT_HOLDER.upper()))

	zax = get_zax_integration()

	if input(
			'Current BTC balance on Bitstamp is {}.\n'
			'Are you sure you want to withdraw it all to {} address {}? (Y/n)\n'.format(
				bitstamp_btc_balance,
				zax.name.title(),
				zax.receiving_address)) != 'Y':
		sys.exit(0)

	try:
		# Double check the address we're sending to is valid on Luno.
		assert (zax.verify_receive_address(zax.receiving_address))

		# Send BTC just bought from Bitstamp over to Luno minus the withdrawal fee.
		bitstamp.withdraw_bitcoin(
			amount=bitstamp_btc_balance - BITSTAMP_WITHDRAWAL_FEE,
			address=zax.receiving_address
		)

		log('Withdrawal complete.')
	except AssertionError as e:
		log('{} withdrawal address not found to be valid. Withdrawal not performed.'.format(zax_name, e), level='w', sms=True)
	except Exception as e:
		log('Something went wrong withdrawing the BTC for the most recent order:\n{}'.format(e), level='w', notify=True)


if __name__ == '__main__':
	run()
