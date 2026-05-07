# NSE India Stock Data Scraper

This setup provides access to NSE India stock data using the unofficial `nse` Python library.

## 📁 Files Created

1. **nse_simple.py** - Simple CLI tool for quick data queries
2. **nse_scraper.py** - Full-featured demo script with all functions
3. **nse_env/** - Python virtual environment with required packages
4. **nse_data/** - Folder where downloaded data is saved

## 🚀 Quick Start

Activate the virtual environment first:
```bash
source nse_env/bin/activate
```

Then use the commands below:

### Get Stock Quote
```bash
python nse_simple.py quote RELIANCE
python nse_simple.py quote TCS
python nse_simple.py quote HDFCBANK
```

### Get Top Gainers/Losers
```bash
python nse_simple.py top
```

### Search for a Stock
```bash
python nse_simple.py search "company name"
```

### Get Historical Data (30 days)
```bash
python nse_simple.py history INFY
python nse_simple.py history RELIANCE
```

### Check Market Status
```bash
python nse_simple.py market
```

## 📊 Available Data

- ✅ Real-time stock quotes (OHLCV)
- ✅ Historical stock data
- ✅ Top gainers/losers (NIFTY 50)
- ✅ Market status for all segments
- ✅ Stock search by name/symbol
- ✅ Index data
- ✅ F&O data (option chain)
- ✅ Corporate announcements
- ✅ Shareholding patterns
- ✅ Bhavcopies (daily reports)

## 📈 Sample Output

```
==================================================
  📊 RELIANCE Quote
  🕐 07-May-2026 15:22:26
==================================================
  Open:  ₹1438.8
  High:  ₹1449.5
  Low:   ₹1430.3
  Close: ₹1435.3
  Volume: 12,095,339
==================================================
```

## ⚠️ Rate Limits

- Maximum **3 requests per second**
- For bulk downloads, use after-market hours
- Add 0.5-1 second delay between requests

## 📝 Notes

- This uses the unofficial `nse` library (v2.1.3)
- All data is publicly available from NSE India
- Rate limiting is enforced to prevent getting blocked
- Data is saved as JSON files in `nse_data/` folder

## 🔧 Customization

Edit `nse_simple.py` or `nse_scraper.py` to add your own functions. 
The main class has methods like:
- `quote(symbol)` - Get stock quote
- `equityQuote(symbol)` - Simplified OHLCV data
- `fetch_equity_historical_data(symbol, from_date, to_date)` - Historical data
- `listEquityStocksByIndex(index)` - List stocks in an index
- `gainers(data)` / `losers(data)` - Top movers
- `optionChain(symbol)` - F&O option chain

See full API docs: https://bennythadikaran.github.io/NseIndiaApi/