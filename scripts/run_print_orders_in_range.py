from datetime import timezone

from integrations.bitstamp import BitstampIntegration
from dateutil import parser

from integrations.valr import ValrIntegration
from write_to_sheets import write_trade_date_to_sheet


def run(lower_bound, upper_bound):
	zax_name = input('ZAX?:\n')
	if zax_name.lower() == 'luno':
		zax_integration = ValrIntegration()
	elif zax_name.lower() == 'valr':
		zax_integration = ValrIntegration()
	else:
		raise ValueError('Invalid ZAX')
	bitstamp_integration = BitstampIntegration()

	if lower_bound and upper_bound:
		lower_bound = parser.parse(lower_bound)
		upper_bound = parser.parse(upper_bound)
	else:
		lower_bound = parser.parse(input('Enter lower bound date:\n'))
		upper_bound = parser.parse(input('Enter upper bound date:\n'))

	zax_order_ids = zax_integration.get_order_ids_in_range(lower_bound=lower_bound, upper_bound=upper_bound)
	bitstamp_order_ids = bitstamp_integration.get_order_ids_in_range(lower_bound=lower_bound, upper_bound=upper_bound)

	if input('Write to sheet? (Y/n)\n') == 'Y':
		kwargs = {
			'account_holder': input('Account holder:\n'),
			'initial_rand_value': 1,
			'fiat_currency': '',
			'fiat_bought': 1,
			'fiat_rand_date': lower_bound,
			'zax': zax_integration,
			'bitstamp_order_ids': bitstamp_order_ids,
			'luno_order_ids': zax_order_ids}
		write_trade_date_to_sheet(**kwargs)


if __name__ == '__main__':
	run('2020-07-28', '2020-08-02')
