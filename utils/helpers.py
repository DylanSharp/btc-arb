from functools import wraps

from misc.utils import log, wait


def retry(exceptions, total_tries=50, initial_wait=0.5, backoff_factor=1.05):
	"""
	Call the decorated function and retry on exception, applying an exponential backoff.

	:param exceptions: Exception(s) that trigger a retry, can be a tuple.
	:param total_tries: Total tries.
	:param initial_wait: Time to first retry.
	:param backoff_factor: Backoff multiplier (e.g. value of 2 will double the delay each retry).
	"""

	def retry_decorator(f):

		@wraps(f)
		def func_with_retries(*args, **kwargs):
			tries_remaining = total_tries
			delay = initial_wait

			while tries_remaining > 0:
				try:
					return f(*args, **kwargs)
				except exceptions as e:
					tries_remaining -= 1
					print_args = args if args else 'no args'

					if tries_remaining == 0:
						msg = 'Function: {}\nFailed after {} tries.'.format(
							f.__name__, total_tries)
						log(msg)
						raise

					msg = (
						'Function failed: {fname}\n'
						'Exception: {exc}\n'
						'Retrying in {:.2f} seconds\n'
						'args:\n{print_args}\n'
						'kwargs: {kwargs}\n'.format(
							delay,
							fname=f.__name__,
							exc=e,
							print_args=print_args,
							kwargs=kwargs
						))

				log(msg, level='e')
				wait(delay)
				delay *= backoff_factor

		return func_with_retries

	return retry_decorator


class UnauthorizedError(Exception):
	pass


class TooManyRequestsError(Exception):
	pass


class InsufficientFundsError(Exception):
	pass


class APIError(Exception):
	pass
