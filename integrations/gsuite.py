from __future__ import print_function

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from utils.helpers import retry
from misc.utils import log


def append_row(values, sheet_name, value_input_option='RAW'):
	wks = get_sheet(sheet_name)

	result = wks.append_row(values=values, value_input_option=value_input_option)
	log('Updated {} row(s) and {} cells(s).'.format(
		result['updates']['updatedRows'],
		result['updates']['updatedCells'])
	)
	return result


@retry(Exception)
def get_sheet(sheet_name, spreadsheet_name='Exchange rate data'):
	scope = [
		'https://spreadsheets.google.com/feeds',
		'https://www.googleapis.com/auth/drive',
	]

	credentials = ServiceAccountCredentials.from_json_keyfile_name('config/gsuite_credentials.json', scope)

	gc = gspread.authorize(credentials)

	return gc.open(spreadsheet_name).worksheet(sheet_name)
