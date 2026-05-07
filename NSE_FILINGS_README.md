# NSE Corporate Filings Scraper

This tool fetches corporate filings from NSE India including announcements, board meetings, corporate actions, and circulars.

## 📁 Files Created

- **nse_filings.py** - Main script to pull all filings
- **nse_data/** - All JSON files are saved here

## 🚀 Quick Start

Activate virtual environment:
```bash
source nse_env/bin/activate
```

## 📋 Available Commands

### 1. Corporate Announcements (Latest 20)
```bash
python nse_filings.py announcements
```
Shows latest company announcements with PDF attachments.

### 2. Board Meetings
```bash
python nse_filings.py boardmeetings
```
Shows upcoming board meetings scheduled.

### 3. Corporate Actions
```bash
python nse_filings.py actions
```
Categorized by:
- 💰 Dividends
- 🎁 Bonus issues
- ✂️ Stock splits
- 📝 Rights issues
- 🔄 Mergers

### 4. NSE Circulars
```bash
python nse_filings.py circulars
```
Exchange circulars with downloadable PDFs.

### 5. Shareholding Pattern
```bash
python nse_filings.py shareholding RELIANCE
python nse_filings.py shareholding HDFCBANK
```
Shows promoter, public, and employee trust holdings.

### 6. Complete Stock Summary
```bash
python nse_filings.py stock TCS
python nse_filings.py stock INFY
```
Combines quote, meta info, and shareholding.

### 7. Pull ALL Filings
```bash
python nse_filings.py all
```
Downloads everything:
- corporate_announcements.json
- board_meetings.json
- corporate_actions.json
- nse_circulars.json

## 📊 Sample Output

### Corporate Actions:
```
⚙️  CORPORATE ACTIONS

Total actions: 20

💰 DIVIDENDS (18):
   OFSS: Interim Dividend - Rs 270 Per Share (Ex: 07-May-2026)
   SOMANYCERA: Interim Dividend - Rs 4 Per Share (Ex: 08-May-2026)
   PREMIERENE: Interim Dividend - Re 0.75 Per Share (Ex: 08-May-2026)

📝 RIGHTS (1):
   EFCIL: Rights 8:103 @ Premium Rs 148/-

🔄 MERGERS (1):
   CIGNITITEC: Merger
```

### Shareholding Pattern:
```
👥 SHAREHOLDING PATTERN: RELIANCE

Found 90 quarters of data

📊 As of 31-MAR-2026:
   Promoter & Group: 50%
   Public: 50%
   Employee Trusts: 0%

📊 As of 31-DEC-2025:
   Promoter & Group: 50.01%
   Public: 49.99%
   Employee Trusts: 0%
```

### NSE Circulars:
```
📋 NSE CIRCULARS

📌 May 07, 2026 | NSE/COMP/74099
   Dept: Inspection & Compliance
   Subject: Segmental Surrender of Membership...
   📥 https://nsearchives.nseindia.com/content/circulars/COMP74099.pdf
```

## 🗂️ Data Files

All JSON files saved in `nse_data/`:
- `corporate_announcements.json` - 20 latest announcements
- `board_meetings.json` - Scheduled board meetings
- `corporate_actions.json` - Dividends, bonuses, splits, etc.
- `nse_circulars.json` - Exchange circulars
- `<SYMBOL>_shareholding.json` - Shareholding data for specific stocks
- `<SYMBOL>_complete_filings.json` - Combined summary

## ⚠️ Rate Limits

- Maximum **3 requests per second**
- The library automatically handles rate limiting
- All data is cached as JSON for offline use

## 📈 What You Get

**Corporate Announcements:**
- Financial results
- Board meeting outcomes
- General updates
- Investor presentations
- Newspaper publications
- Dividend announcements

**Corporate Actions:**
- Dividend dates and amounts
- Bonus issues
- Stock splits
- Rights issues
- Mergers
- Interest payments (for bonds)

**Shareholding Data:**
- Promoter holdings %
- Public holdings %
- Employee trust holdings %
- 90 quarters of historical data

**NSE Circulars:**
- Compliance notices
- Listing updates
- Trading regulations
- IPO listings
- F&O adjustments

---

**Note:** This uses the unofficial `nse` Python library. All data is publicly available from NSE India.
