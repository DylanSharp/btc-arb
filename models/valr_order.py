from dateutil import parser

from models.order_base import OrderBase


class ValrOrder(OrderBase):

    def __init__(self, order_dict=None, zax=None, matched_zar=0):
        self.failed_reason = None
        super().__init__(order_dict, zax, matched_zar)

    def populate(self, order_dict):
        type_map = {
            'buy': 'BID',
            'sell': 'ASK',
        }
        self.id = order_dict.get('orderId')
        # When an order is open the key is side and not orderSide.
        self.type = type_map.get(order_dict.get('orderSide')) or type_map.get(order_dict.get('side'))
        self.failed_reason = order_dict.get('failedReason')
        self.state = order_dict.get('orderStatusType')
        self.pair = order_dict.get('currencyPair')

        self.limit_price = float(order_dict.get('originalPrice', 0))
        self.limit_volume = float(order_dict.get('originalQuantity', 0)) - float(order_dict.get('remainingQuantity', 0))

        self.zar = self.limit_price * self.limit_volume
        self.fee_zar = float(order_dict.get('totalFee', 0)) if order_dict.get('feeCurrency') == 'ZAR' else 0

        self.btc = float(order_dict.get('originalQuantity', 0)) - float(order_dict.get('remainingQuantity', 0))
        self.fee_btc = float(order_dict.get('totalFee', 0)) if order_dict.get('feeCurrency') == 'BTC' else 0

        # Open orders have createdAt key instead of orderCreatedAt.
        self.creation_timestamp = parser.parse(order_dict.get('orderCreatedAt')) if order_dict.get(
            'orderCreatedAt') else parser.parse(order_dict.get('createdAt'))
        # Open orders have no orderUpdatedAt key.
        self.completed_timestamp = parser.parse(order_dict.get('orderUpdatedAt')) if order_dict.get(
            'orderUpdatedAt') else None

        # TODO: This may not be necessary
        # If type is 'BID' negate values (for trade records)
        if self.type == 'BID':
            self.zar *= -1
            self.btc *= -1

    @property
    def is_unfilled(self):
        return self.state == 'Placed'

    @property
    def is_partially_filled(self):
        return self.state == 'Partially Filled'

    @property
    def is_cancelled(self):
        return self.state == 'Cancelled' and self.zar == 0

    @property
    def is_complete(self):
        return self.state == 'Filled'
