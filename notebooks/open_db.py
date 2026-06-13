import sqlite3
import pandas as pd

conn = sqlite3.connect("data/raw/social_orders.db")
df = pd.read_sql("SELECT * FROM social_orders LIMIT 5", conn)
print(df)
conn.close()