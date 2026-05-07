#!/usr/bin/env python3
"""
Fetch all filings for a specific company (announcements, actions, etc.)
Usage: python fetch_company_filings.py <SYMBOL>
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path
from nse import NSE

DOWNLOAD_FOLDER = Path("/root/.openclaw/workspace/nse_data")

def fetch_company_filings(symbol):
    symbol = symbol.upper()
    company_folder = DOWNLOAD_FOLDER / symbol.lower()
    company_folder.mkdir(exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"📥 FETCHING ALL FILINGS FOR: {symbol}")
    print(f"{'='*60}\n")
    
    with NSE(download_folder=DOWNLOAD_FOLDER, server=True) as nse:
        results = {}
        
        # 1. Announcements
        print("🔍 Checking announcements...")
        try:
            all_announcements = nse.announcements()
            company_announcements = [a for a in all_announcements if a.get('symbol') == symbol]
            results['announcements'] = company_announcements
            print(f"   ✅ Found {len(company_announcements)} announcements")
            
            for item in company_announcements[:5]:
                print(f"   📅 {item.get('an_dt', 'N/A')}: {item.get('desc', 'N/A')[:60]}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 2. Corporate Actions
        print("\n🔍 Checking corporate actions...")
        try:
            all_actions = nse.actions()
            company_actions = [a for a in all_actions if a.get('symbol') == symbol]
            results['corporate_actions'] = company_actions
            print(f"   ✅ Found {len(company_actions)} actions")
            
            for item in company_actions:
                print(f"   ⚙️  {item.get('subject', 'N/A')} (Ex: {item.get('exDate', 'N/A')})")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 3. Board Meetings
        print("\n🔍 Checking board meetings...")
        try:
            all_meetings = nse.boardMeetings()
            company_meetings = [m for m in all_meetings if m.get('symbol') == symbol]
            results['board_meetings'] = company_meetings
            print(f"   ✅ Found {len(company_meetings)} meetings")
            
            for item in company_meetings[:5]:
                print(f"   📅 {item.get('bm_date', 'N/A')}: {item.get('purpose', 'N/A')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 4. Current Quote
        print("\n💰 Current quote...")
        try:
            quote = nse.equityQuote(symbol)
            results['quote'] = quote
            print(f"   ✅ Current: ₹{quote['close']} (Vol: {quote['volume']:,})")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 5. Historical Data (90 days)
        print("\n📊 Historical data (90 days)...")
        try:
            to_date = date.today()
            from_date = to_date - timedelta(days=90)
            hist = nse.fetch_equity_historical_data(symbol, from_date, to_date)
            results['historical_90d'] = hist
            print(f"   ✅ {len(hist)} trading days")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 6. Shareholding
        print("\n👥 Shareholding pattern...")
        try:
            sh = nse.shareholding(symbol)
            results['shareholding'] = sh
            print(f"   ✅ {len(sh)} quarters")
            if sh:
                print(f"      Latest: Promoter {sh[0].get('pr_and_prgrp', 'N/A')}%, Public {sh[0].get('public_val', 'N/A')}%")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 7. Company Info
        print("\n🏢 Company info...")
        try:
            meta = nse.equityMetaInfo(symbol)
            results['company_info'] = meta
            print(f"   ✅ {meta.get('companyName', 'N/A')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Save all data
    print("\n" + "="*60)
    print("💾 SAVING FILES...")
    print("="*60)
    
    # Save combined file
    master_file = company_folder / f"{symbol.lower()}_all_filings.json"
    with open(master_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n✅ Master file: {master_file}")
    
    # Individual JSON files
    for key, data in results.items():
        if data:
            filepath = company_folder / f"{symbol.lower()}_{key}.json"
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            print(f"✅ {key}: {len(data) if isinstance(data, list) else 'saved'}")
    
    # Summary
    print("\n" + "="*60)
    print("📊 FINAL SUMMARY")
    print("="*60)
    print(f"\nCompany: {symbol}")
    print(f"Full Name: {results.get('company_info', {}).get('companyName', 'N/A')}")
    print(f"Industry: {results.get('company_info', {}).get('industry', 'N/A')}")
    print(f"\nFiles Found:")
    print(f"  📢 Announcements: {len(results.get('announcements', []))}")
    print(f"  ⚙️  Corporate Actions: {len(results.get('corporate_actions', []))}")
    print(f"  📅 Board Meetings: {len(results.get('board_meetings', []))}")
    print(f"  📊 Historical Days: {len(results.get('historical_90d', []))}")
    print(f"  👥 Shareholding Quarters: {len(results.get('shareholding', []))}")
    print(f"\nCurrent Price: ₹{results.get('quote', {}).get('close', 'N/A')}")
    print(f"\nOutput folder: {company_folder}")
    print("="*60 + "\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_company_filings.py <SYMBOL>")
        print("Example: python fetch_company_filings.py LAURUSLABS")
        sys.exit(1)
    
    fetch_company_filings(sys.argv[1])
