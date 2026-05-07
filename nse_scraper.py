#!/usr/bin/env python3
"""
NSE India Stock Data Scraper
Using the unofficial nse library
"""

import json
from datetime import date, timedelta
from pathlib import Path
from nse import NSE

# Create download folder
DOWNLOAD_FOLDER = Path("/root/.openclaw/workspace/nse_data")
DOWNLOAD_FOLDER.mkdir(exist_ok=True)

class NSEDataScraper:
    def __init__(self):
        # Initialize NSE API (server=True for cloud environments)
        self.nse = NSE(download_folder=DOWNLOAD_FOLDER, server=True)
        
    def get_market_status(self):
        """Get current market status for all segments"""
        print("\n" + "="*50)
        print("MARKET STATUS")
        print("="*50)
        status = self.nse.status()
        for segment in status:
            print(f"\n{segment['market']}: {segment['marketStatus']}")
            if 'marketStatusMessage' in segment:
                print(f"  Message: {segment['marketStatusMessage']}")
        return status
    
    def lookup_symbol(self, query):
        """Search for stock symbol by name or symbol"""
        print(f"\n" + "="*50)
        print(f"LOOKUP: {query}")
        print("="*50)
        result = self.nse.lookup(query)
        if result['symbols']:
            print(f"\nFound {len(result['symbols'])} result(s):")
            for item in result['symbols'][:5]:  # Show top 5
                print(f"  - {item['symbol']} : {item['symbol_info']}")
        else:
            print("No results found")
        return result
    
    def get_stock_quote(self, symbol):
        """Get real-time stock quote"""
        print(f"\n" + "="*50)
        print(f"STOCK QUOTE: {symbol}")
        print("="*50)
        quote = self.nse.quote(symbol, section='trade_info')
        
        if 'priceInfo' in quote:
            price_info = quote['priceInfo']
            print(f"\n  Symbol: {symbol}")
            print(f"  Last Price: ₹{price_info.get('lastPrice', 'N/A')}")
            print(f"  Open: ₹{price_info.get('open', 'N/A')}")
            print(f"  High: ₹{price_info.get('dayHigh', 'N/A')}")
            print(f"  Low: ₹{price_info.get('dayLow', 'N/A')}")
            print(f"  Close: ₹{price_info.get('close', 'N/A')}")
            print(f"  Change: {price_info.get('change', 'N/A')} ({price_info.get('pChange', 'N/A')}%)")
        
        if 'marketDeptOrderBook' in quote:
            trade_info = quote['marketDeptOrderBook'].get('tradeInfo', {})
            if trade_info:
                print(f"\n  Volume: {trade_info.get('totalTradedVolume', 'N/A')}")
                print(f"  Delivery Volume: {trade_info.get('deliveryQuantity', 'N/A')}")
                print(f"  Delivery %: {trade_info.get('deliveryToTradedQuantity', 'N/A')}%")
                print(f"  Total Traded Value: ₹{trade_info.get('totalTradedValue', 'N/A')}")
        
        return quote
    
    def get_historical_data(self, symbol, days=30):
        """Get historical stock data"""
        print(f"\n" + "="*50)
        print(f"HISTORICAL DATA: {symbol} (Last {days} days)")
        print("="*50)
        
        to_date = date.today()
        from_date = to_date - timedelta(days=days)
        
        data = self.nse.fetch_equity_historical_data(
            symbol=symbol,
            from_date=from_date,
            to_date=to_date
        )
        
        if data:
            print(f"\nFound {len(data)} records")
            print("\nRecent data:")
        if data:
            print(f"\nFound {len(data)} records")
            print("\nRecent OHLCV data:")
            for record in data[-5:]:  # Show last 5 records
                ts = record.get('mtimestamp', record.get('CH_TIMESTAMP', 'N/A'))
                open_p = record.get('chOpeningPrice', record.get('CH_OPENING_PRICE', 'N/A'))
                high = record.get('chTradeHighPrice', record.get('CH_TRADE_HIGH_PRICE', 'N/A'))
                low = record.get('chTradeLowPrice', record.get('CH_TRADE_LOW_PRICE', 'N/A'))
                close = record.get('chClosingPrice', record.get('CH_CLOSING_PRICE', 'N/A'))
                vol = record.get('chTotTradedQty', record.get('CH_TOT_TRADED_QTY', 'N/A'))
                print(f"  {ts}: O:₹{open_p} H:₹{high} L:₹{low} C:₹{close} Vol:{vol:,}")
        return data
    
    def get_top_gainers_losers(self):
        """Get today's top gainers and losers"""
        print("\n" + "="*50)
        print("TOP GAINERS & LOSERS")
        print("="*50)
        
        # Get NIFTY 50 stocks
        nifty_data = self.nse.listEquityStocksByIndex(index='NIFTY 50')
        
        # Top gainers
        gainers = self.nse.gainers(nifty_data, count=5)
        print("\n📈 TOP 5 GAINERS (NIFTY 50):")
        for stock in gainers:
            print(f"  {stock['symbol']}: +{stock.get('pChange', 0):.2f}% "
                  f"(₹{stock.get('lastPrice', 0):.2f})")
        
        # Top losers
        losers = self.nse.losers(nifty_data, count=5)
        print("\n📉 TOP 5 LOSERS (NIFTY 50):")
        for stock in losers:
            print(f"  {stock['symbol']}: {stock.get('pChange', 0):.2f}% "
                  f"(₹{stock.get('lastPrice', 0):.2f})")
        
        return {'gainers': gainers, 'losers': losers}
    
    def get_indices(self):
        """List all NSE indices"""
        print("\n" + "="*50)
        print("NSE INDICES")
        print("="*50)
        
        indices_data = self.nse.listIndices()
        print(f"\nTotal indices: {len(indices_data.get('data', []))}")
        
        # Show some popular ones
        popular = ['NIFTY 50', 'NIFTY BANK', 'NIFTY IT', 'NIFTY NEXT 50', 
                   'NIFTY MIDCAP 100', 'NIFTY SMALLCAP 100']
        
        print("\nPopular indices:")
        for idx in indices_data.get('data', []):
            if idx['indexName'] in popular:
                print(f"  {idx['indexName']}: {idx.get('last', 'N/A')} "
                      f"({idx.get('percentChange', 'N/A')}%)")
        
        return indices_data
    
    def get_stock_info(self, symbol):
        """Get comprehensive stock info"""
        print(f"\n" + "="*50)
        print(f"COMPREHENSIVE INFO: {symbol}")
        print("="*50)
        
        # Meta info
        meta = self.nse.equityMetaInfo(symbol)
        if meta:
            print(f"\n Company: {meta.get('companyName', 'N/A')}")
            print(f"  Symbol: {meta.get('symbol', 'N/A')}")
            print(f"  Industry: {meta.get('industry', 'N/A')}")
            print(f"  Sector: {meta.get('sector', 'N/A')}")
            print(f"  ISIN: {meta.get('isinCode', 'N/A')}")
            print(f"  Status: {meta.get('status', 'N/A')}")
        
        # Shareholding pattern
        shareholding = self.nse.shareholding(symbol)
        if shareholding:
            print(f"\n  Shareholding (Latest Quarter):")
            latest = shareholding[0]
            print(f"    Promoter: {latest.get('pr_and_prgrp', 'N/A')}%")
            print(f"    Public: {latest.get('public_val', 'N/A')}%")
            print(f"    Employee Trusts: {latest.get('employeeTrusts', 'N/A')}%")
        
        return {'meta': meta, 'shareholding': shareholding}
    
    def get_option_chain(self, symbol):
        """Get option chain data for F&O stocks"""
        print(f"\n" + "="*50)
        print(f"OPTION CHAIN: {symbol}")
        print("="*50)
        
        try:
            option_chain = self.nse.optionChain(symbol)
            print(f"\nExpiry Dates: {option_chain.get('expiryDates', [])}")
            
            data = option_chain.get('data', [])
            if data:
                print(f"\nTotal strikes: {len(data)}")
                print("\nSample strikes:")
                for strike in data[:3]:
                    ce = strike.get('CE', {})
                    pe = strike.get('PE', {})
                    strike_price = strike.get('strikePrice', 'N/A')
                    print(f"\n  Strike: {strike_price}")
                    print(f"    CE: OI {ce.get('openInterest', 0)}, "
                          f"Vol {ce.get('totalTradedVolume', 0)}, "
                          f"LTP {ce.get('lastPrice', 0)}")
                    print(f"    PE: OI {pe.get('openInterest', 0)}, "
                          f"Vol {pe.get('totalTradedVolume', 0)}, "
                          f"LTP {pe.get('lastPrice', 0)}")
            return option_chain
        except Exception as e:
            print(f"Error fetching option chain: {e}")
            return None
    
    def save_data(self, data, filename):
        """Save data to JSON file"""
        filepath = DOWNLOAD_FOLDER / filename
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"\n✓ Saved to: {filepath}")
        return filepath
    
    def close(self):
        """Close the NSE connection"""
        self.nse.exit()


def demo():
    """Run a demo of NSE data fetching"""
    print("="*50)
    print("NSE INDIA DATA SCRAPER DEMO")
    print("="*50)
    
    scraper = NSEDataScraper()
    
    try:
        # 1. Market Status
        scraper.get_market_status()
        
        # 2. Lookup a stock
        scraper.lookup_symbol("hdfcbank")
        
        # 3. Get stock quote
        scraper.get_stock_quote("HDFCBANK")
        
        # 4. Historical data
        data = scraper.get_historical_data("RELIANCE", days=10)
        scraper.save_data(data, "reliance_historical.json")
        
        # 5. Top gainers and losers
        scraper.get_top_gainers_losers()
        
        # 6. Indices
        scraper.get_indices()
        
        # 7. Comprehensive stock info
        scraper.get_stock_info("TCS")
        
        # 8. Option chain (for F&O stocks)
        scraper.get_option_chain("NIFTY")
        
    except Exception as e:
        print(f"\nError: {e}")
    
    finally:
        scraper.close()
        print("\n" + "="*50)
        print("DONE! Data saved to:", DOWNLOAD_FOLDER)
        print("="*50)


if __name__ == "__main__":
    demo()
