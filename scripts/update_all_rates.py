from datetime import datetime
from gspread import Cell

from integrations.gsuite import get_sheet
from integrations.cexio import get_tickers as get_cex_tickers
from integrations.luno import get_tickers as get_luno_tickers
from integrations.ovex import get_tickers as get_ovex_tickers
from integrations.fixer import get_tickers as get_fixer_tickers
from integrations.bittrex import get_tickers as get_bittrex_tickers
from integrations.bitstamp import get_tickers as get_bitstamp_tickers
from integrations.kraken import get_tickers as get_kraken_tickers
from integrations.binance import get_tickers as get_binance_tickers


if __name__ == '__main__':
	rates_sheet = get_sheet('Rates', 'rates')
	row = 3
	col = 2
	
	print('Getting tickers ...')

	ovex_tickers = get_ovex_tickers()
	luno_tickers = get_luno_tickers()
	cex_tickers = get_cex_tickers()
	fixer_tickers = get_fixer_tickers()
	bittrex_tickers = get_bittrex_tickers()
	bitstamp_tickers = get_bitstamp_tickers()
	kraken_tickers = get_kraken_tickers()
	binance_tickers = get_binance_tickers()
	binance_tickers_je = get_binance_tickers(je=True)

	print('Writing to sheet ...')

	def update():
		rates_sheet.update_cells(pair_cells)
		rates_sheet.update_cells(value_cells)

	# Ovex
	pair_cells = [Cell(row=row + i, col=col+1, value=ticker[0]) for i, ticker in enumerate(ovex_tickers)]
	value_cells = [Cell(row=row + i, col=col+2, value=ticker[1]) for i, ticker in enumerate(ovex_tickers)]
	update()

	col += 3

	# Luno
	pair_cells = [Cell(row=row + i, col=col+1, value=ticker['pair']) for i, ticker in enumerate(luno_tickers)]
	value_cells = [Cell(row=row + i, col=col+2, value=ticker['ask']) for i, ticker in enumerate(luno_tickers)]
	update()

	col += 3

	# CEX.io
	pair_cells = [Cell(row=row + i, col=col+1, value=ticker['pair']) for i, ticker in enumerate(cex_tickers)]
	value_cells = [Cell(row=row + i, col=col+2, value=ticker['ask']) for i, ticker in enumerate(cex_tickers)]
	update()

	col += 3

	# Bittrex
	pair_cells = [Cell(row=row + i, col=col+1, value=ticker['MarketName']) for i, ticker in enumerate(bittrex_tickers)]
	value_cells = [Cell(row=row + i, col=col+2, value=ticker['Ask']) for i, ticker in enumerate(bittrex_tickers)]
	update()

	col += 3

	# Bitstamp
	pair_cells = [Cell(row=row + i, col=col+1, value=ticker['pair']) for i, ticker in enumerate(bitstamp_tickers)]
	value_cells = [Cell(row=row + i, col=col+2, value=ticker['ask']) for i, ticker in enumerate(bitstamp_tickers)]
	update()

	col += 3

	# Kraken
	pair_cells = [Cell(row=row + i, col=col+1, value=ticker['pair']) for i, ticker in enumerate(kraken_tickers)]
	value_cells = [Cell(row=row + i, col=col+2, value=ticker['ask']) for i, ticker in enumerate(kraken_tickers)]
	update()

	col += 3

	# Binance
	pair_cells = [Cell(row=row + i, col=col+1, value=ticker['symbol']) for i, ticker in enumerate(binance_tickers)]
	value_cells = [Cell(row=row + i, col=col+2, value=ticker['price']) for i, ticker in enumerate(binance_tickers)]
	update()

	col += 3

	# Binance JE
	pair_cells = [Cell(row=row + i, col=col+1, value=ticker['symbol']) for i, ticker in enumerate(binance_tickers_je)]
	value_cells = [Cell(row=row + i, col=col+2, value=ticker['price']) for i, ticker in enumerate(binance_tickers_je)]
	update()

	col += 3

	# # Fixer
	pair_cells = [Cell(row=row + i, col=col+1, value='ZAR/' + pair[0]) for i, pair in enumerate(fixer_tickers.items())]
	value_cells = [Cell(row=row + i, col=col+2, value=pair[1]) for i, pair in enumerate(fixer_tickers.items())]
	update()

	# Update "last updated" cell.
	rates_sheet.update_cell(2, 1, datetime.now().strftime('%Y/%m/%d, %H:%M:%S'))
	print('Done.')















