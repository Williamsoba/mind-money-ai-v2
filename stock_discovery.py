import yfinance as yf
import pandas as pd
import json
import requests
import os
from datetime import datetime, timezone

# Starter universe: diversified research candidates.
# This is a screening universe, not a buy list.
TICKERS = [
    "NVDA", "AMD", "AVGO", "MU", "PLTR",
    "CRWD", "NET", "SOFI", "HOOD", "RKLB",
    "ASTS", "IONQ", "TEM", "HIMS", "CAVA",
    "CELH", "ELF", "GE", "VST", "CEG",
    "NEE", "ETN", "PWR", "JPM", "NU",
    "MELI", "SHOP", "TOST", "UBER", "GOOGL"
]

WEIGHTS = {
    "growth": 25,
    "momentum": 20,
    "volume": 15,
    "financial_health": 20,
    "valuation": 15,
    "industry": 5
}

def safe_number(value):
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None

def growth_score(value):
    if value is None:
        return None
    if value >= 0.25:
        return 100
    if value >= 0.10:
        return 80
    if value > 0:
        return 60
    if value > -0.10:
        return 30
    return 0

def momentum_score(momentum):
    if momentum is None:
        return None
    if momentum >= 0.30:
        return 100
    if momentum >= 0.15:
        return 80
    if momentum > 0:
        return 60
    if momentum > -0.10:
        return 30
    return 0

def get_financial_growth(statement, row_name):
    try:
        row = statement.loc[row_name].dropna()

        if len(row) < 2:
            return None

        newest = float(row.iloc[0])
        previous = float(row.iloc[1])

        if abs(previous) < 1:
            return None

        if newest * previous < 0:
            return None

        if newest < 0 and previous < 0:
            return None

        return (newest / previous) - 1

    except (KeyError, IndexError, TypeError, ValueError):
        return None


FMP_WORKER_URL = "https://mind-money-api.williamsob777.workers.dev"


def get_fmp_records(endpoint, symbol):
    """Retrieve annual financial statements through our Cloudflare Worker."""
    try:
        response = requests.get(
            f"{FMP_WORKER_URL}/api/{endpoint}",
            params={"symbol": symbol},
            timeout=20
        )
        response.raise_for_status()
        payload = response.json()

        if not isinstance(payload, list):
            return []

        # Only compare annual fiscal-year records.
        annual = [
            item for item in payload
            if isinstance(item, dict)
            and str(item.get("period", "")).upper() in ("FY", "ANNUAL")
        ]

        return sorted(
            annual,
            key=lambda item: item.get("date", ""),
            reverse=True
        )

    except (requests.RequestException, ValueError, TypeError) as error:
        print(f"FMP {endpoint} unavailable for {symbol}: {error}")
        return []


def get_fmp_financials(symbol):
    """Get income and balance-sheet records from FMP."""
    income = get_fmp_records("income", symbol)
    balance = get_fmp_records("balance", symbol)

    return {
        "income": income,
        "balance": balance
    }


def fmp_growth(latest, previous, field):
    """Calculate growth only when both annual values are positive."""
    try:
        newest = float(latest[field])
        older = float(previous[field])

        if older <= 1 or newest <= 0:
            return None

        return (newest / older) - 1

    except (KeyError, TypeError, ValueError):
        return None


def fmp_number(record, field):
    """Safely read a numeric FMP field."""
    if not record:
        return None

    try:
        value = record.get(field)
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def analyze_stock(symbol):
    print(f"Scanning {symbol}...")

    stock = yf.Ticker(symbol)

    history = stock.history(period="1y", auto_adjust=True)

    if history.empty or len(history) < 130:
        return None

    info = stock.info or {}
    prices = history["Close"].dropna()
    volumes = history["Volume"].dropna()

    current_price = safe_number(prices.iloc[-1])
    if not current_price or current_price <= 0:
        return None

    momentum_1m = current_price / prices.iloc[-22] - 1
    momentum_3m = current_price / prices.iloc[-64] - 1
    momentum_6m = current_price / prices.iloc[-126] - 1

    average_volume = safe_number(volumes.tail(20).mean())
    previous_volume = safe_number(volumes.iloc[-40:-20].mean())

    volume_change = None
    if previous_volume and previous_volume > 0:
        volume_change = average_volume / previous_volume - 1

    market_cap = safe_number(info.get("marketCap"))

    if market_cap is None:
        cap_category = "Unknown"
    elif market_cap < 2_000_000_000:
        cap_category = "Small"
    elif market_cap < 10_000_000_000:
        cap_category = "Mid"
    else:
        cap_category = "Large"

    # FMP is the primary source for annual fundamentals.
    # Yahoo Finance remains the fallback.
    fmp = get_fmp_financials(symbol)

    income_records = fmp["income"]
    balance_records = fmp["balance"]

    latest_income = income_records[0] if income_records else None
    previous_income = income_records[1] if len(income_records) > 1 else None
    latest_balance = balance_records[0] if balance_records else None

    revenue_growth = None
    earnings_growth = None

    if latest_income and previous_income:
        revenue_growth = fmp_growth(
            latest_income, previous_income, "revenue"
        )
        earnings_growth = fmp_growth(
            latest_income, previous_income, "netIncome"
        )

    # Fall back to Yahoo for any growth metric FMP could not provide.
    financials = stock.financials

    if revenue_growth is None:
        revenue_growth = get_financial_growth(
            financials, "Total Revenue"
        )

    if earnings_growth is None:
        earnings_growth = get_financial_growth(
            financials, "Net Income"
        )


    growth_warnings = []

    if revenue_growth is not None and abs(revenue_growth) > 2:
        growth_warnings.append("Extreme revenue growth")

    if earnings_growth is not None and abs(earnings_growth) > 2:
        growth_warnings.append("Extreme earnings growth")

    growth_values = [
        growth_score(revenue_growth),
        growth_score(earnings_growth)
    ]
    growth_values = [x for x in growth_values if x is not None]

    growth = (
        sum(growth_values) / len(growth_values)
        if growth_values else None
    )

    momentum = momentum_score(
        (momentum_1m + momentum_3m + momentum_6m) / 3
    )

    volume = None
    if volume_change is not None:
        if volume_change >= 0.50:
            volume = 100
        elif volume_change >= 0.20:
            volume = 80
        elif volume_change > 0:
            volume = 60
        elif volume_change > -0.20:
            volume = 40
        else:
            volume = 20

    cash = fmp_number(
        latest_balance, "cashAndShortTermInvestments"
    )

    if cash is None and latest_balance:
        cash_equivalents = fmp_number(
            latest_balance, "cashAndCashEquivalents"
        )
        short_investments = fmp_number(
            latest_balance, "shortTermInvestments"
        )

        if cash_equivalents is not None:
            cash = cash_equivalents + (short_investments or 0)

    debt = fmp_number(latest_balance, "totalDebt")

    if cash is None:
        cash = safe_number(info.get("totalCash"))

    if debt is None:
        debt = safe_number(info.get("totalDebt"))


    financial_health = None
    if cash is not None and debt is not None:
        if debt == 0:
            financial_health = 100
        elif cash >= debt:
            financial_health = 100
        elif cash >= debt * 0.5:
            financial_health = 70
        elif cash >= debt * 0.2:
            financial_health = 40
        else:
            financial_health = 15

    pe = safe_number(info.get("forwardPE"))
    valuation = None

    if pe is not None and pe > 0:
        if pe <= 15:
            valuation = 100
        elif pe <= 25:
            valuation = 80
        elif pe <= 35:
            valuation = 60
        elif pe <= 50:
            valuation = 35
        else:
            valuation = 15

    # Industry growth is not yet independently measured.
    # Leave it unavailable instead of inventing a score.
    scores = {
        "growth": growth,
        "momentum": momentum,
        "volume": volume,
        "financial_health": financial_health,
        "valuation": valuation
    }

    available = {
        key: value for key, value in scores.items()
        if value is not None
    }

    total_weight = sum(WEIGHTS[key] for key in available)

    score = None
    if total_weight:
        score = sum(
            value * WEIGHTS[key]
            for key, value in available.items()
        ) / total_weight

    missing_categories = [
        key for key, value in scores.items()
        if value is None
    ]

    completeness_pct = (
        len(available) / len(scores) * 100
        if scores else 0
    )

    if len(missing_categories) >= 2:
        research_data_warning = "High"
    elif len(missing_categories) == 1:
        research_data_warning = "Moderate"
    else:
        research_data_warning = "Low"

    return {
        "ticker": symbol,
        "company": info.get("shortName", symbol),
        "sector": info.get("sector", "Unknown"),
        "market_cap_category": cap_category,
        "market_cap": market_cap,
        "price": round(current_price, 2),
        "momentum_1m": round(momentum_1m * 100, 2),
        "momentum_3m": round(momentum_3m * 100, 2),
        "momentum_6m": round(momentum_6m * 100, 2),
        "volume_change": (
            round(volume_change * 100, 2)
            if volume_change is not None else None
        ),
        "revenue_growth": (
            round(revenue_growth * 100, 2)
            if revenue_growth is not None else None
        ),
        "earnings_growth": (
            round(earnings_growth * 100, 2)
            if earnings_growth is not None else None
        ),
        "cash": cash,
        "debt": debt,
        "forward_pe": pe,
        "financial_data_source": (
            "FMP via Cloudflare"
            if latest_income or latest_balance
            else "Yahoo Finance fallback"
        ),
        "fmp_income_date": (
            latest_income.get("date") if latest_income else None
        ),
        "fmp_balance_date": (
            latest_balance.get("date") if latest_balance else None
        ),
        "fmp_revenue": fmp_number(latest_income, "revenue"),
        "fmp_net_income": fmp_number(latest_income, "netIncome"),
        "fmp_cash_and_short_term_investments": cash,
        "fmp_total_debt": debt,
        "score": round(score, 1) if score is not None else None,
        "growth_warning": (
            "; ".join(growth_warnings)
            if growth_warnings else "None"
        ),
        "categories_available": ", ".join(available.keys()),
        "categories_missing": ", ".join(missing_categories) or "None",
        "data_completeness_pct": round(completeness_pct, 1),
        "research_data_warning": research_data_warning,
        "data_completeness": (
            f"{len(available)}/{len(scores)} categories scored"
        ),
        "scan_time_utc": datetime.now(
            timezone.utc
        ).isoformat()
    }

def main():
    os.makedirs("data", exist_ok=True)
    os.makedirs("reports", exist_ok=True)

    results = []

    for symbol in TICKERS:
        try:
            result = analyze_stock(symbol)
            if result:
                results.append(result)
        except Exception as error:
            print(f"Skipped {symbol}: {error}")

    if not results:
        print("No results. Check your internet connection.")
        return

    df = pd.DataFrame(results)

    df = df.sort_values(
        "score", ascending=False, na_position="last"
    )

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y-%m-%d"
    )

    csv_file = f"reports/weekly_{timestamp}.csv"
    df.to_csv(csv_file, index=False)

    history_file = "data/discovery_history.csv"

    if os.path.exists(history_file):
        df.to_csv(
            history_file,
            mode="a",
            header=False,
            index=False
        )
    else:
        df.to_csv(history_file, index=False)

    print("\nMIND & MONEY AI")
    print("WEEKLY STOCK DISCOVERY")
    print("=" * 60)

    print(df[
        ["ticker", "company", "market_cap_category",
         "price", "momentum_3m", "score"]
    ].head(20).to_string(index=False))

    print(f"\nReport saved: {csv_file}")
    print(f"History saved: {history_file}")

if __name__ == "__main__":
    main()

