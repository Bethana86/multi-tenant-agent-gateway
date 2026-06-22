import sqlite3
import os
import datetime

db_path = os.path.join(os.path.dirname(__file__), "fincorp.db")

def init_db():
    print(f"Initializing SQLite database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create stock forecast table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_forecasts (
            ticker TEXT,
            timestamp TEXT,
            forecast_value REAL,
            confidence_lower REAL,
            confidence_upper REAL
        )
    """)
    
    # Create market news table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_news (
            ticker TEXT,
            headline TEXT,
            sentiment TEXT,
            timestamp TEXT
        )
    """)
    
    # Check if table already has data
    cursor.execute("SELECT COUNT(*) FROM stock_forecasts")
    if cursor.fetchone()[0] == 0:
        print("Populating stock_forecasts table...")
        # Populate with mock data for various stock tickers
        base_date = datetime.datetime(2026, 6, 20)
        data = []
        tickers = {
            "GOOGL": 175.50,
            "AAPL": 182.20,
            "MSFT": 415.80,
            "AMZN": 180.10
        }
        for ticker, base_price in tickers.items():
            for day in range(14):
                ts = (base_date + datetime.timedelta(days=day)).strftime("%Y-%m-%d")
                price = base_price + (day * 1.5) - ( (day % 3) * 0.8 )
                lower = price * 0.97
                upper = price * 1.03
                data.append((ticker, ts, round(price, 2), round(lower, 2), round(upper, 2)))
        
        cursor.executemany("""
            INSERT INTO stock_forecasts (ticker, timestamp, forecast_value, confidence_lower, confidence_upper)
            VALUES (?, ?, ?, ?, ?)
        """, data)
        
        # Populate news
        print("Populating market_news table...")
        news = [
            ("GOOGL", "FinCorp upgrades GOOGL target to $210, citing strong Cloud AI performance.", "Bullish", "2026-06-21"),
            ("AAPL", "Apple announces new Siri integration using Edge devices.", "Bullish", "2026-06-20"),
            ("MSFT", "Microsoft signs multi-year enterprise AI licensing deal.", "Bullish", "2026-06-22"),
            ("AMZN", "Amazon reports slight warehouse supply chain delay in EU.", "Neutral", "2026-06-19")
        ]
        cursor.executemany("""
            INSERT INTO market_news (ticker, headline, sentiment, timestamp)
            VALUES (?, ?, ?, ?)
        """, news)
        
        conn.commit()
        print("Data populated successfully.")
    else:
        print("Database already initialized and populated.")
    
    conn.close()

if __name__ == "__main__":
    init_db()
