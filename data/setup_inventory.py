# data/setup_inventory.py
"""
Creates the SQLite inventory database for local development.
Simulates SAP inventory : swappable via adapter pattern in production.

Run once: python data/setup_inventory.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "inventory.db"

def setup():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            item        TEXT PRIMARY KEY,
            stock       INTEGER NOT NULL,
            unit_price  REAL NOT NULL
        )
    """)

    # Acme Corp approved inventory
    items = [
        ("WidgetA",  50,  250.00),
        ("WidgetB",  50,  500.00),
        ("GadgetX",   5,  750.00),
        ("FakeItem",  0,    0.00),  # zero stock to trigger fraud flag
    ]

    cursor.executemany(
        "INSERT OR REPLACE INTO inventory (item, stock, unit_price) VALUES (?, ?, ?)",
        items
    )

    conn.commit()
    conn.close()

    print(f"Inventory database created at: {DB_PATH}")
    print("Items loaded:")
    for item, stock, price in items:
        print(f"  {item:<12} stock: {stock:>3}   unit price: ${price:,.2f}")

if __name__ == "__main__":
    setup()