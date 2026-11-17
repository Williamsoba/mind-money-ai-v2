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

df = df.astype(object).where(pd.notna(df), None)

payload = {
    "project": "Mind & Money AI",
    "version": "2.0",
    "report": os.path.basename(latest_file),
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "source": "Yahoo Finance via yfinance",
    "disclaimer": (
        "Experimental research screener. "
        "Scores are heuristic, not investment advice."
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
print("Output: frontend/data/latest.json")
