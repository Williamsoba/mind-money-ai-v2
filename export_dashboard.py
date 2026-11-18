import json
import glob
import os
import pandas as pd
from datetime import datetime, timezone

files = sorted(glob.glob("reports/weekly_*.csv"))

if not files:
    raise SystemExit("No weekly reports found in reports/")

latest_file = files[-1]
df = pd.read_csv(latest_file)

# Identify FMP coverage.
if "fmp_income_date" in df.columns:
    income = df["fmp_income_date"].notna()
else:
    income = pd.Series(False, index=df.index)

if "fmp_balance_date" in df.columns:
    balance = df["fmp_balance_date"].notna()
else:
    balance = pd.Series(False, index=df.index)

both = income & balance

if "financial_data_source" in df.columns:
    fmp_count = int(
        (df["financial_data_source"] == "FMP via Cloudflare").sum()
    )
else:
    fmp_count = 0

yahoo_count = len(df) - fmp_count

fmp_symbols = (
    df.loc[both, "ticker"].dropna().tolist()
    if "ticker" in df.columns else []
)

# Convert missing values to JSON null.
df = df.astype(object).where(pd.notna(df), None)

payload = {
    "project": "Mind & Money AI",
    "version": "2.1",
    "report": os.path.basename(latest_file),
    "generated_at": datetime.now(timezone.utc).isoformat(),

    "source": (
        "Yahoo Finance via yfinance for market data; "
        "FMP via Cloudflare for available financial fundamentals, "
        "with Yahoo Finance fallback."
    ),

    "data_sources": {
        "market_data": "Yahoo Finance via yfinance",
        "fundamentals_primary": "Financial Modeling Prep via Cloudflare",
        "fundamentals_fallback": "Yahoo Finance via yfinance"
    },

    "financial_data_coverage": {
        "total_stocks": len(df),
        "fmp_stocks": fmp_count,
        "yahoo_fallback_stocks": yahoo_count,
        "fmp_income_statements": int(income.sum()),
        "fmp_balance_sheets": int(balance.sum()),
        "fmp_both_statements": int(both.sum()),
        "fmp_symbols": fmp_symbols
    },

    "disclaimer": (
        "Experimental research screener. "
        "Scores are heuristic, data availability varies by provider, "
        "and results are not investment advice."
    ),

    "total_stocks": len(df),
    "stocks": df.to_dict(orient="records")
}

os.makedirs("frontend/data", exist_ok=True)

with open("frontend/data/latest.json", "w") as f:
    json.dump(payload, f, indent=2, allow_nan=False)

print("Dashboard data exported successfully.")
print("Source report:", latest_file)
print("Stocks exported:", len(df))
print("FMP stocks:", fmp_count)
print("Yahoo fallback stocks:", yahoo_count)
print("FMP complete statements:", int(both.sum()))
print("Output: frontend/data/latest.json")
