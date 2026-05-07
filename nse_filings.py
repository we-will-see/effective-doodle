#!/usr/bin/env python3
"""
NSE Corporate Filings Scraper
Fetch corporate announcements, board meetings, annual reports, and shareholding data
"""

import json
from datetime import date, timedelta
from pathlib import Path
from nse import NSE

DOWNLOAD_FOLDER = Path("/root/.openclaw/workspace/nse_data")
DOWNLOAD_FOLDER.mkdir(exist_ok=True)

class NSEFilingsScraper:
    def __init__(self):
        self.nse = NSE(download_folder=DOWNLOAD_FOLDER, server=True)
    
    def get_corporate_announcements(self, symbol=None, days=7):
        """Get corporate announcements for a stock or all stocks"""
        print(f"\n{'='*60}")
        print(f"📢 CORPORATE ANNOUNCEMENTS")
        if symbol:
            print(f"Symbol: {symbol.upper()}")
        print(f"{'='*60}")
        
        try:
            data = self.nse.announcements()
            
            if data and isinstance(data, list):
                print(f"\nTotal announcements: {len(data)}\n")
                
                for item in data[:20]:
                    symbol_name = item.get('symbol', 'N/A')
                    desc = item.get('desc', 'N/A')
                    dt = item.get('an_dt', 'N/A')[:10]
                    attachment = item.get('attchmntFile', '')
                    
                    print(f"📅 {dt} | {symbol_name}")
                    print(f"   {desc[:100]}{'...' if len(desc) > 100 else ''}")
                    if attachment and attachment != '-':
                        print(f"   📎 {attachment}")
                    print()
                
                self._save_json(data, "corporate_announcements.json")
            else:
                print("No announcements found")
            
            return data
        except Exception as e:
            print(f"Error fetching announcements: {e}")
            return None
    
    def get_board_meetings(self, from_date=None, to_date=None):
        """Get board meeting announcements"""
        print(f"\n{'='*60}")
        print(f"📅 BOARD MEETINGS")
        print(f"{'='*60}")
        
        try:
            data = self.nse.boardMeetings()
            
            if data and isinstance(data, list):
                print(f"\nTotal board meetings: {len(data)}\n")
                
                for item in data[:15]:
                    symbol = item.get('symbol', 'N/A')
                    purpose = item.get('purpose', 'N/A')
                    meeting_date = item.get('bm_date', 'N/A')
                    company = item.get('company', item.get('sm_name', item.get('smDesc', 'N/A')))
                    
                    print(f"📆 {meeting_date}")
                    print(f"   Company: {company}")
                    if symbol != 'N/A':
                        print(f"   Symbol: {symbol}")
                    if purpose != 'N/A':
                        print(f"   Purpose: {purpose}")
                    print()
                
                self._save_json(data, "board_meetings.json")
            else:
                print("No board meetings found")
            
            return data
        except Exception as e:
            print(f"Error fetching board meetings: {e}")
            return None
    
    def get_corporate_actions(self, from_date=None, to_date=None):
        """Get corporate actions (dividends, splits, bonuses)"""
        print(f"\n{'='*60}")
        print(f"⚙️  CORPORATE ACTIONS")
        print(f"{'='*60}")
        
        try:
            data = self.nse.actions()
            
            if data and isinstance(data, list):
                print(f"\nTotal actions: {len(data)}\n")
                
                # Categorize by action type
                dividends = [i for i in data if 'dividend' in i.get('subject', '').lower() or 'interest' in i.get('subject', '').lower()]
                bonuses = [i for i in data if 'bonus' in i.get('subject', '').lower()]
                splits = [i for i in data if 'split' in i.get('subject', '').lower() or 'face value' in i.get('subject', '').lower()]
                rights = [i for i in data if 'right' in i.get('subject', '').lower()]
                mergers = [i for i in data if 'merger' in i.get('subject', '').lower()]
                others = [i for i in data if i not in dividends + bonuses + splits + rights + mergers]
                
                if dividends:
                    print(f"💰 DIVIDENDS ({len(dividends)}):")
                    for item in dividends[:5]:
                        print(f"   {item['symbol']}: {item['subject']} (Ex: {item.get('exDate', 'N/A')})")
                    print()
                
                if bonuses:
                    print(f"🎁 BONUSES ({len(bonuses)}):")
                    for item in bonuses:
                        print(f"   {item['symbol']}: {item['subject']}")
                    print()
                
                if splits:
                    print(f"✂️  SPLITS ({len(splits)}):")
                    for item in splits:
                        print(f"   {item['symbol']}: {item['subject']}")
                    print()
                
                if rights:
                    print(f"📝 RIGHTS ({len(rights)}):")
                    for item in rights:
                        print(f"   {item['symbol']}: {item['subject']}")
                    print()
                
                if mergers:
                    print(f"🔄 MERGERS ({len(mergers)}):")
                    for item in mergers:
                        print(f"   {item['symbol']}: {item['subject']}")
                    print()
                
                self._save_json(data, "corporate_actions.json")
            else:
                print("No corporate actions found")
            
            return data
        except Exception as e:
            print(f"Error fetching corporate actions: {e}")
            return None
    
    def get_nse_circulars(self):
        """Get NSE circulars and notices"""
        print(f"\n{'='*60}")
        print(f"📋 NSE CIRCULARS")
        print(f"{'='*60}")
        
        try:
            response = self.nse.circulars()
            
            if response and isinstance(response, dict) and 'data' in response:
                data = response['data']
                print(f"\nTotal circulars: {len(data)}\n")
                
                for item in data[:15]:
                    dept = item.get('circDepartment', item.get('dept', 'N/A'))
                    subject = item.get('sub', item.get('subject', 'N/A'))
                    circ_date = item.get('cirDisplayDate', item.get('circDate', 'N/A'))
                    file_url = item.get('circFilelink', item.get('fileURL', ''))
                    circ_num = item.get('circDisplayNo', item.get('circNumber', 'N/A'))
                    
                    print(f"📌 {circ_date} | {circ_num}")
                    print(f"   Dept: {dept}")
                    print(f"   Subject: {subject[:80]}{'...' if len(subject) > 80 else ''}")
                    if file_url:
                        print(f"   📥 {file_url}")
                    print()
                
                self._save_json(response, "nse_circulars.json")
            else:
                print("No circulars found")
            
            return response
        except Exception as e:
            print(f"Error fetching circulars: {e}")
            return None
    
    def get_shareholding_pattern(self, symbol):
        """Get shareholding pattern for a specific stock"""
        print(f"\n{'='*60}")
        print(f"👥 SHAREHOLDING PATTERN: {symbol.upper()}")
        print(f"{'='*60}")
        
        try:
            data = self.nse.shareholding(symbol.upper())
            
            if data:
                print(f"\nFound {len(data)} quarters of data\n")
                
                for item in data[:4]:
                    quarter_date = item.get('date', 'N/A')
                    promoter = item.get('pr_and_prgrp', 'N/A')
                    public_sh = item.get('public_val', 'N/A')
                    employee = item.get('employeeTrusts', 'N/A')
                    
                    print(f"📊 As of {quarter_date}:")
                    print(f"   Promoter & Group: {promoter}%")
                    print(f"   Public: {public_sh}%")
                    print(f"   Employee Trusts: {employee}%")
                    print()
                
                self._save_json(data, f"{symbol.lower()}_shareholding.json")
            else:
                print("No shareholding data found")
            
            return data
        except Exception as e:
            print(f"Error fetching shareholding: {e}")
            return None
    
    def get_stock_filings_summary(self, symbol):
        """Get all filings for a specific stock"""
        print(f"\n{'='*60}")
        print(f"📑 COMPLETE FILINGS SUMMARY: {symbol.upper()}")
        print(f"{'='*60}")
        
        results = {}
        
        # Get stock quote
        try:
            quote = self.nse.equityQuote(symbol.upper())
            print(f"\n📊 Current Price: ₹{quote.get('close', 'N/A')}")
            results['quote'] = quote
        except Exception as e:
            print(f"Quote error: {e}")
        
        # Get meta info
        try:
            meta = self.nse.equityMetaInfo(symbol.upper())
            print(f"🏢 Company: {meta.get('companyName', 'N/A')}")
            print(f"🏭 Industry: {meta.get('industry', 'N/A')}")
            results['meta'] = meta
        except Exception as e:
            print(f"Meta error: {e}")
        
        # Get shareholding
        try:
            shareholding = self.nse.shareholding(symbol.upper())
            if shareholding:
                print(f"👥 Latest Shareholding: Q{shareholding[0].get('date', 'N/A')}")
            results['shareholding'] = shareholding
        except Exception as e:
            print(f"Shareholding error: {e}")
        
        # Save combined file
        self._save_json(results, f"{symbol.lower()}_complete_filings.json")
        
        return results
    
    def _save_json(self, data, filename):
        """Save data to JSON file"""
        filepath = DOWNLOAD_FOLDER / filename
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"✅ Saved to: {filepath}\n")
    
    def close(self):
        self.nse.exit()


def print_menu():
    print("""
╔══════════════════════════════════════════════════════════════╗
║              NSE INDIA FILINGS SCRAPER                         ║
╠══════════════════════════════════════════════════════════════╣
║  1. Corporate Announcements    - Latest company announcements  ║
║  2. Board Meetings             - Upcoming board meetings       ║
║  3. Corporate Actions          - Dividends, bonuses, splits    ║
║  4. NSE Circulars              - Exchange circulars/notices    ║
║  5. Shareholding Pattern       - For specific stock            ║
║  6. Complete Stock Filings     - All data for one stock        ║
║  7. Pull ALL Filings           - Download everything           ║
║  0. Exit                                                        ║
╚══════════════════════════════════════════════════════════════╝
    """)


def main():
    import sys
    
    scraper = NSEFilingsScraper()
    
    try:
        # Check if command line args provided
        if len(sys.argv) > 1:
            command = sys.argv[1].lower()
            
            if command == 'announcements':
                scraper.get_corporate_announcements()
            elif command == 'boardmeetings':
                scraper.get_board_meetings()
            elif command == 'actions':
                scraper.get_corporate_actions()
            elif command == 'circulars':
                scraper.get_nse_circulars()
            elif command == 'shareholding' and len(sys.argv) > 2:
                scraper.get_shareholding_pattern(sys.argv[2])
            elif command == 'stock' and len(sys.argv) > 2:
                scraper.get_stock_filings_summary(sys.argv[2])
            elif command == 'all':
                print("\n📥 PULLING ALL FILINGS... This may take a moment.\n")
                scraper.get_corporate_announcements()
                scraper.get_board_meetings()
                scraper.get_corporate_actions()
                scraper.get_nse_circulars()
                print("\n✅ ALL FILINGS DOWNLOADED!")
            else:
                print("Usage:")
                print("  python nse_filings.py announcements")
                print("  python nse_filings.py boardmeetings")
                print("  python nse_filings.py actions")
                print("  python nse_filings.py circulars")
                print("  python nse_filings.py shareholding <SYMBOL>")
                print("  python nse_filings.py stock <SYMBOL>")
                print("  python nse_filings.py all")
        else:
            # Interactive mode
            while True:
                print_menu()
                choice = input("Enter choice (0-7): ").strip()
                
                if choice == '1':
                    scraper.get_corporate_announcements()
                elif choice == '2':
                    scraper.get_board_meetings()
                elif choice == '3':
                    scraper.get_corporate_actions()
                elif choice == '4':
                    scraper.get_nse_circulars()
                elif choice == '5':
                    symbol = input("Enter stock symbol: ").strip()
                    if symbol:
                        scraper.get_shareholding_pattern(symbol)
                elif choice == '6':
                    symbol = input("Enter stock symbol: ").strip()
                    if symbol:
                        scraper.get_stock_filings_summary(symbol)
                elif choice == '7':
                    print("\n📥 PULLING ALL FILINGS...\n")
                    scraper.get_corporate_announcements()
                    scraper.get_board_meetings()
                    scraper.get_corporate_actions()
                    scraper.get_nse_circulars()
                    print("\n✅ ALL FILINGS DOWNLOADED!")
                elif choice == '0':
                    break
                else:
                    print("Invalid choice!")
                
                input("\nPress Enter to continue...")
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    finally:
        scraper.close()
        print("\nDone!")


if __name__ == "__main__":
    main()
