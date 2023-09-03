import sys

from integrations.luno import LunoIntegration
from integrations.valr import ValrIntegration
from misc.utils import log


def get_zax_integration():
    name = input('VALR or Luno?:\n')
    name = name.lower()
    if name == 'luno':
        return LunoIntegration()
    if name == 'valr':
        return ValrIntegration()
    else:
        log('Not a valid exchange.')
        sys.exit(0)
