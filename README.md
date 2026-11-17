# Mind & Money AI — Version 2

A free-first personal wealth research project with a Python stock discovery engine.

## Current features

- Scans a starter universe of 30 publicly traded companies.
- Reviews revenue and earnings growth.
- Calculates 1-month, 3-month and 6-month price momentum.
- Compares recent trading volume.
- Evaluates a basic cash-versus-debt measure.
- Uses forward P/E as a basic valuation indicator.
- Produces research scores and data-completeness warnings.
- Saves dated CSV research reports and a local history file.

## Technology

- Python
- pandas
- yfinance

## Setup

Clone the repository:

    git clone YOUR_GITHUB_REPOSITORY_URL
    cd mind-money-ai-v2

Create a virtual environment:

    python3 -m venv venv
    source venv/bin/activate

Install dependencies:

    pip install -r requirements.txt

Run the scanner:

    python stock_discovery.py

Reports are saved locally in the reports/ directory.
Historical results are saved in data/.

## Important limitations

This is an experimental research screener, not a trading system or
investment recommendation.

The initial universe contains only 30 tickers and is not a
market-wide stock scan.

Market data is obtained through yfinance, an unofficial interface
to Yahoo Finance. Data may be delayed, incomplete, unavailable,
or subject to provider restrictions.

Scores are heuristic and should not be interpreted as probabilities
of investment success. Always independently verify company filings,
financial statements, valuation and risks.

## Roadmap

- Improve scoring reliability and research warnings.
- Expand the stock universe across sectors and market caps.
- Build a web research dashboard.
- Connect a secure backend.
- Automate weekly reports.
- Add optional AI-assisted company research.
