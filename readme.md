# Arbitrage Trading Bot

### Why is this public?
This code was originally never meant to be made public because I created it and was using it myself. However, market 
conditions have changed and it's no longer very profitable to do this trade so I don't have a use for it anymore.

I decided to make it public because I haven't been very good at building up a public portfolio of my work and this may 
contribute. It was only ever intended for my eyes only so comments and docstrings are minimal and there are some pretty 
ugly logs spewed out into the terminal which was my crude but effective way of monitoring a trade.

### What does/did it do?
The arbitrage involves 3 currencies, the Rand, Bitcoin and usually USD but I sometimes used EUR too.

Essentially, due to capital controls in South Africa, there is a profit to be made if you can get Rand out of the 
country (relatively easy but lots of red tape). 
One first buys USD and then uses the USD to buy Bitcoin in the foreign market. The bitcoin is then sent back into South 
Africa where it is sold for a profit (hopefully).

This project served to automate this process for me and more importantly time the buys/sells optimally to optimise 
profits. The most complex part of it involves placing an order on an exchange and then monitoring that order 
(by polling) to check if it has been filled or if it's moved from the top of the order book.

The biggest challenge was handling all the different states that the order might be in while ensuring that money is not 
lost. I used this code for about 2 years and it did very well for me.

### Code breakdown
Most of the magic happens in ***models/trade.py*** and ***models/base_trade.py***. This is where the core algorithm for starting, 
monitoring and completing a trade lives.

There are a lot of integrations with 3rd parties and exchanges so each has its own module. The ones that I didn't use 
much just have some simple wrappers but the three that I used most are created with an object-oriented approach, 
namely: ***integrations/luno.py***, ***integrations/valr.py*** and ***integrations/bitstamp.py***

There are also object-oriented models of an "order" for each major exchange.

I ran this code on an aws hosted linux server and would just execute the trades by running the scripts via the terminal
via SSH.
