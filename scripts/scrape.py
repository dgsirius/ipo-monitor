import json
import os
import re
import sys
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

CALENDAR_URL = "https://stockanalysis.com/ipos/calendar/"
EDGAR_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
HEADERS = {
    "User-Agent": "ipo-monitor/1.0 research@example.com",
    "Accept-Language": "en-US,en;q=0.9",
}


def _parse_date(raw: str) -> str:
    """Convert 'Apr 15, 2026' -> '2026-04-15'. Returns raw if parse fails."""
    raw = raw.strip()
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw


def _parse_table(table) -> list:
    """Parse an IPO HTML table into list of dicts."""
    headers_raw = [th.get_text(strip=True) for th in table.select("thead th")]
    field_map = {
        "IPO Date": "ipo_date",
        "Symbol": "symbol",
        "Company Name": "company",
        "Exchange": "exchange",
        "Price Range": "price_range",
        "Shares Offered": "shares_offered",
        "Deal Size": "deal_size",
        "Market Cap": "market_cap",
        "Revenue": "revenue",
    }
    fields = [field_map.get(h, h.lower().replace(" ", "_")) for h in headers_raw]

    rows = []
    for tr in table.select("tbody tr"):
        cells = [td.get_text(strip=True) for td in tr.select("td")]
        if not cells:
            continue
        row = dict(zip(fields, cells))
        if "ipo_date" in row:
            row["ipo_date"] = _parse_date(row["ipo_date"])
        row.setdefault("sec_filing_url", None)
        row.setdefault("sec_raw_excerpt", None)
        row.setdefault("analysis", None)
        rows.append(row)
    return rows


def parse_ipo_calendar(url: str = CALENDAR_URL) -> list:
    """Fetch IPO calendar and return list of IPO dicts (this week + next week)."""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    ipos = []
    for heading in soup.find_all(["h2", "h3"]):
        text = heading.get_text(strip=True).lower()
        if "this week" in text or "next week" in text:
            table = heading.find_next("table")
            if table:
                ipos.extend(_parse_table(table))
    return ipos
