import requests

from utils.helpers import TooManyRequestsError, UnauthorizedError


def request(*args, **kwargs):
	"""
	A wrapper of requests in order that does things required for all endpoints.

	:param args:
	:param kwargs:
	:return:
	"""

	# Set default timeout to 5 seconds so that connections don't end up hanging.
	timeout = kwargs.pop('timeout', 5)
	verb = args[0].upper()
	args = args[1:]
	verb_map = {
		'DELETE': requests.delete,
		'GET': requests.get,
		'PATCH': requests.patch,
		'POST': requests.post,
		'PUT': requests.put,
	}
	response = verb_map[verb](*args, **kwargs, timeout=timeout)

	if response.status_code == 401:
		raise UnauthorizedError()
	if response.status_code == 429:
		# We want to retry if the error was unrelated to the order itself.
		raise TooManyRequestsError()

	return response


def get_request(*args, **kwargs):
	return request('GET', *args, **kwargs)


def post_request(*args, **kwargs):
	return request('POST', *args, **kwargs)


def delete_request(*args, **kwargs):
	return request('DELETE', *args, **kwargs)


def patch_request(*args, **kwargs):
	return request('PATCH', *args, **kwargs)


def put_request(*args, **kwargs):
	return request('PUT', *args, **kwargs)
