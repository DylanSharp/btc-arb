import json
import urllib
import httplib2

import settings
from misc import utils


def send_request(to, content, method='GET'):
    """
    Run the HTTP request against the Clickatell API.

    :return: The request response
    """

    data = {
        'to': to,
        'content': content,
        'apiKey': settings.CLICKATEL_API_KEY
    }

    http = httplib2.Http()
    body = urllib.parse.urlencode(data)
    url = 'https://platform.clickatell.com/messages/http/send'
    url = url + '?' + body
    resp, content = http.request(url, method, body=json.dumps(data))
    resp['body'] = content
    return resp


def send_sms(msg, max_retries=5):
    content = msg + '\n-BitBot'
    to = ['27741821742']

    attempts = 1
    while attempts < max_retries + 1:
        try:
            utils.log('Sending message to {}:\n{}'.format(to, msg))
            result = send_request(to, content)

            if result.status != 202:
                raise ValueError('Received response status of {}'.format(result.status))

            return result

        except Exception as e:
            utils.log('Failed to send sms on attempt {}.\n{}'.format(attempts, e), level='w')
            attempts += 1


if __name__ == '__main__':
    send_sms('Test message.')
