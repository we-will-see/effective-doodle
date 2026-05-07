#!/usr/bin/env python3
"""
Download all Laurus Labs filings for last 90 days
"""

import json
from datetime import date, timedelta
from pathlib import Path
from nse import NSE

DOWNLOAD_FOLDER = Path("/root/.openclaw/workspace/nse_data/laurus_labs")
DOWNLOAD_FOLDER.mkdir(exist_ok=True)

SYMBOL = "LAURUSLABS"

def download_laurus_filings():
    print(f"\n{'='*60}")
    print(f"📥 DOWNLOADING {SYMBOL} FILINGS (Last 90 Days)")
    print(f"{'='*60}\n")
    
    results = {}
    
    with NSE(download_folder=DOWNLOAD_FOLDER, server=True) as nse:
        # 1. Historical Price Data (90 days)
        print("📊 Fetching historical price data...")
        to_date = date.today()
        from_date = to_date - timedelta(days=90)
        
        try:
            hist_data = nse.fetch_equity_historical_data(SYMBOL, from_date, to_date)
            results['historical_prices'] = hist_data
            print(f"   ✅ {len(hist_data)} trading days of price data")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 2. Current Quote
        print("\n💰 Fetching current quote...")
        try:
            quote = nse.equityQuote(SYMBOL)
            results['current_quote'] = quote
            print(f"   ✅ Current: ₹{quote['close']} (Volume: {quote['volume']:,})")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 3. Company Meta Info
        print("\n🏢 Fetching company information...")
        try:
            meta = nse.equityMetaInfo(SYMBOL)
            results['company_info'] = meta
            print(f"   ✅ {meta.get('companyName', 'N/A')}")
            print(f"      Industry: {meta.get('industry', 'N/A')}")
            print(f"      Status: {meta.get('status', 'N/A')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 4. Shareholding Pattern (all quarters)
        print("\n👥 Fetching shareholding patterns...")
        try:
            shareholding = nse.shareholding(SYMBOL)
            results['shareholding'] = shareholding
            print(f"   ✅ {len(shareholding)} quarters of data")
            
            # Show latest
            if shareholding:
                latest = shareholding[0]
                print(f"   📊 Latest (as of {latest.get('date', 'N/A')}):")
                print(f"      Promoter: {latest.get('pr_and_prgrp', 'N/A')}%")
                print(f"      Public: {latest.get('public_val', 'N/A')}%")
                print(f"      Employee Trusts: {latest.get('employeeTrusts', 'N/A')}%")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 5. Get detailed scrip data (includes full quote info)
        print("\n📋 Fetching detailed scrip data...")
        try:
            detailed = nse.getDetailedScripData(SYMBOL)
            results['detailed_scrip'] = detailed
            print(f"   ✅ Detailed data fetched")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Save everything
    print("\n" + "="*60)
    print("💾 SAVING ALL DATA...")
    print("="*60)
    
    # Master file with everything
    master_file = DOWNLOAD_FOLDER / f"{SYMBOL.lower()}_complete_filings_90days.json"
    with open(master_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n✅ Master file: {master_file}")
    
    # Individual files
    if 'historical_prices' in results:
        with open(DOWNLOAD_FOLDER / f"{SYMBOL.lower()}_historical_prices.json", 'w') as f:
            json.dump(results['historical_prices'], f, indent=2, default=str)
        print(f"✅ Historical prices: {len(results['historical_prices'])} records")
    
    if 'shareholding' in results:
        with open(DOWNLOAD_FOLDER / f"{SYMBOL.lower()}_shareholding.json", 'w') as f:
            json.dump(results['shareholding'], f, indent=2, default=str)
        print(f"✅ Shareholding: {len(results['shareholding'])} quarters")
    
    if 'company_info' in results:
        with open(DOWNLOAD_FOLDER / f"{SYMBOL.lower()}_company_info.json", 'w') as f:
            json.dump(results['company_info'], f, indent=2, default=str)
        print(f"✅ Company info saved")
    
    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    print(f"\nCompany: {results.get('company_info', {}).get('companyName', 'N/A')}")
    print(f"Symbol: {SYMBOL}")
    print(f"Industry: {results.get('company_info', {}).get('industry', 'N/A')}")
    print(f"\nData collected:")
    print(f"  - Historical prices: {len(results.get('historical_prices', []))} days")
    print(f"  - Shareholding: {len(results.get('shareholding', []))} quarters")
    print(f"\nFiles saved to: {DOWNLOAD_FOLDER}")
    print("="*60 + "\n")
    
    return results

if __name__ == "__main__":
    download_laurus_filings()
