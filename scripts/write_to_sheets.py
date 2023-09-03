# - *- coding: utf- 8 - *-
from datetime import datetime, timedelta
from dateutil import parser

import settings
from integrations import gsuite
from integrations.bitstamp import BitstampIntegration
from integrations.fixer import get_historical_ticker
from integrations.gsuite import get_sheet
from misc.utils import log
from models.bitstamp import BitstampOrder


def write_trade_date_to_sheet(
		account_holder,
		initial_rand_value,
		bitstamp_order_ids,
		luno_order_ids,
		fiat_currency,
		zax,
		fiat_bought=1.0,
		fiat_rand_date=None):
	log('Logging trade to google sheets.')
	log('Gathering data ...')

	bitstamp = BitstampIntegration()

	if fiat_rand_date is None:
		fiat_rand_date = datetime.now() - timedelta(days=90)

	# Get deposits
	deposit_transactions = bitstamp.get_user_transactions_by_date_and_type(
		transaction_type='deposit',
		start_date=fiat_rand_date)

	# Get Bitstamp Order(s)
	bitstamp_order_dict = {int(order_id): bitstamp.get_order(order_id) for order_id in bitstamp_order_ids}
	transactions = bitstamp.get_user_transactions()

	# Clear transactions in the order to be refreshed.
	for k, v in bitstamp_order_dict.items():
		bitstamp_order_dict[k].transactions = []

	bitstamp_transactions = []
	# Assign transaction back to the orders
	for txn in transactions:
		if bitstamp_order_dict.get(txn.order_id):
			bitstamp_order_dict[txn.order_id].transactions.append(txn)
			bitstamp_transactions.append(txn)
	bitstamp_orders = [v for k, v in bitstamp_order_dict.items()]
	bitstamp_order = BitstampOrder.combine_orders(bitstamp_orders)

	# Get Luno Order(s)
	zax_orders = [zax.get_order(order_id) for order_id in luno_order_ids]
	zax_order = zax_orders[0].combine_orders(zax_orders)

	rand_fiat_exchange_rate = (initial_rand_value - settings.CURRENCY_DIRECT_FEE) / fiat_bought

	values = [
		fiat_rand_date.strftime('%Y/%m/%d'),  # ZAR-FIAT conversion date
		settings.FIAT_RAND_EXCHANGE,  # ZAR-FIAT exchange
		account_holder.title(),  # Account holder at ZAR-FIAT exchange
		initial_rand_value,  # Initial ZAR invested
		settings.CURRENCY_DIRECT_FEE,  # ZAR-FIAT fee
		fiat_currency.upper(),  # The fiat currency used in the trade (EUR or USD)
		fiat_bought,  # Amount of FIAT bought with ZAR
		get_formula([t.fee for t in deposit_transactions]),  # Deposit fee(s) into FIAT - BTC exchange
		settings.FIAT_BTC_EXCHANGE,  # FIAT-BTC exchange
		bitstamp_order.datetime.strftime('%Y/%m/%d'),  # FIAT-BTC conversion date
		get_formula([txn.btc for txn in bitstamp_transactions]),  # Total bitcoin bought
		bitstamp_order.weighted_average_price,  # Weighted average price of bitcoin bought
		get_formula(o.fees for o in bitstamp_orders),  # Fee(s) paid when buying bitcoin
		get_formula([bitstamp_order.fees, rand_fiat_exchange_rate], symbol='*'),  # Fee(s) in ZAR
		zax_order.completed_timestamp.strftime('%Y/%m/%d'),  # BTC-ZAR conversion date
		'Trading Fee Goes Here',  # Trading Free
		'Trading Fee Paid Checkbox',  # Trading Free Paid Checkbox
		'Copy formula above ^',  # Bitcoin held
		'Copy formula above ^',  # Bitcoin held in ZAR
		get_formula([o.btc for o in zax_orders]),  # Total bitcoin sold
		get_formula([o.zar for o in zax_orders]),  # Total ZAR received for sale of BTC
		zax_order.weighted_average_price,  # Weighted average price received for BTC
		get_formula([o.fee_btc for o in zax_orders]),  # Fee(s) paid for sale of BTC
		zax_order.fee_btc * zax_order.weighted_average_price,  # Fee(s) in ZAR
		settings.LUNO_WITHDRAWAL_FEE,  # Luno withdrawal fee
		'Copy formula above ^',  # Profit in ZAR
		'Copy formula above ^',  # Net profit
		'Copy formula above ^',  # Profit as %
		'\'' + '{}'.format(','.join([str(o) for o in bitstamp_order_ids])),  # Bitstamp order ids (csv)
		'\'' + '{}'.format(','.join([str(o) for o in luno_order_ids])),  # Luno order ids (csv)
	]
	str_values = [str(v) for v in values]

	log('Writing to google sheet ...')
	gsuite.append_row(str_values, sheet_name=account_holder + '_trades', value_input_option='USER_ENTERED')
	log('Sheet updated.')


def get_formula(values, symbol=None):
	if symbol is None:
		symbol = '+'
	str_values = ['{:.8f}'.format(v) if v > 0 else '({:.8f})'.format(v) for v in values]
	return '=' + symbol.join(str_values)


def write_historical_fiat_data(days_back_in_time, start_date=None, starting_row=2):
	sheet = get_sheet('raw_data')

	if start_date is None:
		start_date = datetime.today()

	for i in range(1, days_back_in_time - 1):
		dt = start_date - timedelta(days=i - 1)

		timestamp, rates = get_historical_ticker(dt)
		row = starting_row + i - 1
		cell_list = sheet.range('W{row}:AA{row}'.format(row=row))

		cell_list[0].value = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d')
		cell_list[1].value = round(1 / rates['USD'], 4)
		cell_list[2].value = round(1 / rates['EUR'], 4)
		cell_list[3].value = round(1 / rates['GBP'], 4)
		cell_list[4].value = round(1 / rates['AUD'], 4)

		# Update in batch
		sheet.update_cells(cell_list)
		print(
			row,
			dt.strftime('%Y-%m-%d'),
			round(1 / rates['USD'], 4),
			'Next:',
			((dt - timedelta(days=1)).strftime('%Y-%m-%d')),
			row + 1
		)


if __name__ == '__main__':
	kwargs = {
		'account_holder': 'brad',
		'initial_rand_value': 830000,
		'fiat_currency': 'usd',
		'fiat_bought': 47226.17,
		'fiat_rand_date': parser.parse('2020/06/17'),
		'bitstamp_order_ids': [
			'1244271051452416',
			'1244304621449216',
			'1244333728854016',
			'1244313085382657',
			'1244305469931521',
			'1244337437884416',
			'1244337732132864',
			'1244338523058176',
			'1244339060256768',
			'1244340256571392',
			'1244351221518336',
			'1244354452557825',
		],
		'luno_order_ids': [
			'BXKQZ255DFPKPJB',
			'BXEYWQUYZD9JJ76',
			'BXG68XE7W5S3UPA',
			'BXE8NF7Z8JP236C',
			'BXFC3UJVR7BQY4Z',
			'BXBVWDBHJ6RWWCN',
		]}
	write_trade_date_to_sheet(**kwargs)
