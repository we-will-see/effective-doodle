#!/usr/bin/env python3
"""
NSE India Stock Data Scraper - Simple CLI Version
Usage: python nse_simple.py
"""

import sys
from datetime import date, timedelta
from pathlib import Path
from nse import NSE

DOWNLOAD_FOLDER = Path("/root/.openclaw/workspace/nse_data")
DOWNLOAD_FOLDER.mkdir(exist_ok=True)

def get_quote(symbol):
    """Get real-time stock quote"""
    with NSE(download_folder=DOWNLOAD_FOLDER, server=True) as nse:
        quote = nse.equityQuote(symbol.upper())
        print(f"\n{'='*50}")
        print(f"  📊 {symbol.upper()} Quote")
        print(f"  🕐 {quote.get('date', 'N/A')}")
        print(f"{'='*50}")
        print(f"  Open:  ₹{quote.get('open', 'N/A')}")
        print(f"  High:  ₹{quote.get('high', 'N/A')}")
        print(f"  Low:   ₹{quote.get('low', 'N/A')}")
        print(f"  Close: ₹{quote.get('close', 'N/A')}")
        print(f"  Volume: {quote.get('volume', 0):,}")
        print(f"{'='*50}\n")

def get_top_stocks():
    """Get top gainers and losers"""
    with NSE(download_folder=DOWNLOAD_FOLDER, server=True) as nse:
        nifty_data = nse.listEquityStocksByIndex(index='NIFTY 50')
        gainers = nse.gainers(nifty_data, count=5)
        losers = nse.losers(nifty_data, count=5)
        
        print(f"\n{'='*50}")
        print("  📈 TOP 5 GAINERS (NIFTY 50)")
        print(f"{'='*50}")
        for i, stock in enumerate(gainers, 1):
            print(f"  {i}. {stock['symbol']}: +{stock.get('pChange', 0):.2f}% "
                  f"(₹{stock.get('lastPrice', 0):.2f})")
        
        print(f"\n{'='*50}")
        print("  📉 TOP 5 LOSERS (NIFTY 50)")
        print(f"{'='*50}")
        for i, stock in enumerate(losers, 1):
            print(f"  {i}. {stock['symbol']}: {stock.get('pChange', 0):.2f}% "
                  f"(₹{stock.get('lastPrice', 0):.2f})")
        print(f"{'='*50}\n")

def get_market_status():
    """Get market status"""
    with NSE(download_folder=DOWNLOAD_FOLDER, server=True) as nse:
        status = nse.status()
        print(f"\n{'='*50}")
        print("  🏛️  MARKET STATUS")
        print(f"{'='*50}")
        for segment in status:
            print(f"  {segment['market']}: {segment['marketStatus']}")
        print(f"{'='*50}\n")

def search_stock(query):
    """Search for a stock"""
    with NSE(download_folder=DOWNLOAD_FOLDER, server=True) as nse:
        result = nse.lookup(query)
        if result['symbols']:
            print(f"\n{'='*50}")
            print(f"  🔍 Search Results for '{query}'")
            print(f"{'='*50}")
            for item in result['symbols']:
                print(f"  {item['symbol']} : {item['symbol_info']}")
            print(f"{'='*50}\n")
        else:
            print(f"No results found for '{query}'")

def get_historical(symbol, days=30):
    """Get historical data and save to file"""
    with NSE(download_folder=DOWNLOAD_FOLDER, server=True) as nse:
        to_date = date.today()
        from_date = to_date - timedelta(days=days)
        data = nse.fetch_equity_historical_data(symbol=symbol.upper(), 
                                               from_date=from_date, 
                                               to_date=to_date)
        
        print(f"\n{'='*50}")
        print(f"  📈 Historical Data: {symbol.upper()}")
        print(f"{'='*50}")
        print(f"  Found {len(data)} records\n")
        
        for record in data[-5:]:
            ts = record.get('mtimestamp', 'N/A')
            open_p = record.get('chOpeningPrice', 'N/A')
            high = record.get('chTradeHighPrice', 'N/A')
            low = record.get('chTradeLowPrice', 'N/A')
            close = record.get('chClosingPrice', 'N/A')
            vol = record.get('chTotTradedQty', 0)
            print(f"  {ts}: O:₹{open_p} H:₹{high} L:₹{low} C:₹{close} Vol:{vol:,}")
        
        # Save to file
        import json
        filepath = DOWNLOAD_FOLDER / f"{symbol.lower()}_historical.json"
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"\n  ✓ Saved to: {filepath}")
        print(f"{'='*50}\n")

def main():
    if len(sys.argv) < 2:
        print("""
NSE Stock Data Scraper

Usage:
  python nse_simple.py quote <SYMBOL>     - Get real-time quote
  python nse_simple.py top                - Get top gainers/losers
  python nse_simple.py market             - Get market status
  python nse_simple.py search <QUERY>   - Search for a stock
  python nse_simple.py history <SYMBOL>   - Get 30-day historical data

Examples:
  python nse_simple.py quote RELIANCE
  python nse_simple.py search hdfc
  python nse_simple.py history TCS
        """)
        return
    
    command = sys.argv[1].lower()
    
    if command == 'quote' and len(sys.argv) >= 3:
        get_quote(sys.argv[2])
    elif command == 'top':
        get_top_stocks()
    elif command == 'market':
        get_market_status()
    elif command == 'search' and len(sys.argv) >= 3:
        search_stock(sys.argv[2])
    elif command == 'history' and len(sys.argv) >= 3:
        get_historical(sys.argv[2])
    else:
        print("Invalid command or missing argument. Run without arguments for help.")

if __name__ == "__main__":
    main()
