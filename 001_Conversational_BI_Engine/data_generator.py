import numpy as np
import pandas as pd
import os

np.random.seed(42)
n_rows = 1500

dates = pd.date_range(start="2024-01-01", end="2024-12-31", periods=n_rows)
regions = np.random.choice(["North", "South", "East", "West"], size=n_rows, p=[0.35, 0.25, 0.20, 0.20])
categories = np.random.choice(["Electronics", "Apparel", "Home Goods", "Office Supplies"], size=n_rows)
channels = np.random.choice(["Direct Web", "Amazon", "Retail Partner"], size=n_rows, p=[0.50, 0.35, 0.15])

units_sold = np.random.randint(1, 15, size=n_rows)
unit_price = np.random.uniform(15.0, 350.0, size=n_rows).round(2)
discount_pct = np.random.choice([0.0, 0.05, 0.10, 0.20], size=n_rows, p=[0.4, 0.3, 0.2, 0.1])

gross_sales = (units_sold * unit_price).round(2)
revenue = (gross_sales * (1 - discount_pct)).round(2)
cogs = (revenue * np.random.uniform(0.55, 0.75, size=n_rows)).round(2)
profit = (revenue - cogs).round(2)

df = pd.DataFrame({
    "Order_Date": dates.strftime("%Y-%m-%d"),
    "Region": regions,
    "Category": categories,
    "Sales_Channel": channels,
    "Units_Sold": units_sold,
    "Unit_Price": unit_price,
    "Discount_Pct": discount_pct,
    "Revenue": revenue,
    "Profit": profit
})

os.makedirs("data", exist_ok=True)
output_path = os.path.join("data", "ecommerce_business_data.csv")
df.to_csv(output_path, index=False)
print(f"Dataset successfully created at: {output_path} ({len(df)} rows)")