import sys

from integrations.helpers import get_zax_integration
from misc.utils import log


def run():
	zax_integration = get_zax_integration()
	open_orders = zax_integration.get_open_orders()

	log('Found {} active order(s)'.format(len(open_orders)))

	if input('Cancel all? (Y/n)\n') != 'Y':
		sys.exit(0)

	for order in open_orders:
		order.cancel()

	log('Complete.')


if __name__ == '__main__':
	run()
