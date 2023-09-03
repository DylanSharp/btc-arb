import sys

from integrations.valr import ValrIntegration
from misc.utils import log, spacer
from settings import ACCOUNT_HOLDER

order_templates = [
    (0.122648, 775000),
    (0.122648, 790500),
    (0.122648, 806000),
    (0.122648, 821500),
    (0.122648, 837000),
    (0.122648, 852500),
    (0.122648, 868000),
]
num_orders = len(order_templates)


def run():
    log(spacer)
    log('Batch Orders', color='cyan')
    valr = ValrIntegration()

    log('{} orders found to be placed.'.format(num_orders))
    count = 0

    for ot in order_templates:
        amount = ot[0]
        price = ot[1]
        if input(
                'Place order on {}''s account:'
                '\nAmount: {} BTC'
                '\nPrice: R{:.2f}'
                '\nConfirm? (Y/n)\n'.format(ACCOUNT_HOLDER, amount, price)) != 'Y':
            sys.exit(0)
        order = valr.sell_limit_order(btc_amount=amount, price=price, post_only=True)
        log('Order created on VALR:\n'
            'ID: {}\n'
            'Status: {}\n'
            'Price: {}\n'
            'Amount: {}'.format(order.id, order.state, order.limit_price, order.btc))
        count += 1
        log('{} of {} orders placed.'.format(count, num_orders))


if __name__ == '__main__':
    run()
