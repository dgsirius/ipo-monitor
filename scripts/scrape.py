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
    "User-Agent": "IPOMonitor research@ipomonitor.io",
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


def search_edgar(symbol: str, company: str) -> str | None:
    """
    Search SEC EDGAR for S-1/F-1 filing. Returns main document URL or None.
    Tries symbol first, then company name.

    The EDGAR full-text search index (efts.sec.gov/LATEST/search-index) returns
    _source fields: 'ciks' (list), 'adsh' (accession number with dashes),
    'form' (filing type).  These differ from the legacy field names 'entity_id',
    'accession_no', and 'form_type' that were previously used.
    """
    today = datetime.utcnow().strftime("%Y-%m-%d")
    start = (datetime.utcnow() - timedelta(days=365)).strftime("%Y-%m-%d")

    for query in [f'"{symbol}"', f'"{company}"']:
        params = {
            "q": query,
            "forms": "S-1,S-1/A,F-1,F-1/A",
            "dateRange": "custom",
            "startdt": start,
            "enddt": today,
        }
        try:
            resp = requests.get(EDGAR_SEARCH_URL, params=params, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            hits = resp.json().get("hits", {}).get("hits", [])
            if hits:
                src = hits[0]["_source"]
                # ciks is a list of zero-padded CIK strings, e.g. ["0002096300"]
                ciks = src.get("ciks") or []
                cik = str(ciks[0]).lstrip("0") if ciks else "0"
                # adsh is the accession number with dashes, e.g. "0001234567-26-000001"
                accession = src.get("adsh", "")
                doc_url = _get_main_doc_url(cik, accession)
                return doc_url
        except Exception as e:
            print(f"[scrape] EDGAR search failed for {query}: {e}")
    return None


def _get_main_doc_url(cik: str, accession_no: str) -> str | None:
    """
    Fetch filing index and return URL of largest .htm file (the main S-1 document).
    accession_no: original format with dashes, e.g. '0001234567-26-000001'
    """
    accession_nodash = accession_no.replace("-", "")
    # Correct SEC EDGAR index URL: uses nodash dir + original-with-dashes filename
    index_url = (
        f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_nodash}/"
        f"{accession_no}-index.htm"
    )
    try:
        resp = requests.get(index_url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        best_url = None
        best_size = 0
        for row in soup.select("table tr"):
            cells = row.select("td")
            if len(cells) >= 3:
                link = row.select_one("a[href$='.htm']")
                if link:
                    try:
                        size = int(cells[-1].get_text(strip=True).replace(",", ""))
                    except ValueError:
                        size = 0
                    if size > best_size:
                        best_size = size
                        href = link.get("href", "")
                        if href.startswith("http"):
                            best_url = href
                        else:
                            best_url = f"https://www.sec.gov{href}"
        return best_url
    except Exception as e:
        print(f"[scrape] Filing index fetch failed: {e}")
        return None


SECTION_KEYWORDS = {
    "business": ["BUSINESS"],
    "risks": ["RISK FACTORS"],
    "financials": ["RESULTS OF OPERATIONS", "SELECTED FINANCIAL DATA", "FINANCIAL STATEMENTS"],
}


def fetch_s1_excerpt(url: str) -> str:
    """
    Download S-1 HTML and extract Business + Risk Factors + Financials sections.
    Returns combined text (<=3000 chars). Returns "" on any failure.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        full_text = soup.get_text(separator="\n", strip=True)
    except Exception as e:
        print(f"[scrape] S-1 download failed for {url}: {e}")
        return ""

    parts = []
    for section_name, keywords in SECTION_KEYWORDS.items():
        for kw in keywords:
            idx = full_text.upper().find(kw)
            if idx != -1:
                excerpt = full_text[idx: idx + 1000].strip()
                parts.append(excerpt)
                break

    return "\n\n".join(parts)[:3000]  # hard cap per spec §5.3


def run_scrape(data_dir: str = "data", week_date: str | None = None) -> str:
    """
    Full scrape pipeline. Returns path to written JSON file.
    week_date: 'YYYY-MM-DD', defaults to today.
    """
    if week_date is None:
        week_date = datetime.utcnow().strftime("%Y-%m-%d")

    print(f"[scrape] Fetching IPO calendar...")
    ipos = parse_ipo_calendar()
    print(f"[scrape] Found {len(ipos)} IPOs")

    for ipo in ipos:
        symbol = ipo.get("symbol", "")
        company = ipo.get("company", "")
        print(f"[scrape] Searching EDGAR for {symbol} ({company})...")
        filing_url = search_edgar(symbol, company)
        ipo["sec_filing_url"] = filing_url
        if filing_url:
            print(f"[scrape] Fetching S-1 excerpt for {symbol}...")
            ipo["sec_raw_excerpt"] = fetch_s1_excerpt(filing_url)
        else:
            print(f"[scrape] No EDGAR filing found for {symbol}")
            ipo["sec_raw_excerpt"] = None

    os.makedirs(data_dir, exist_ok=True)
    out_path = os.path.join(data_dir, f"{week_date}.json")
    payload = {
        "week": week_date,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "ai_analyzed_at": None,
        "ipo_count": len(ipos),
        "ipos": ipos,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[scrape] Wrote {out_path}")
    return out_path


if __name__ == "__main__":
    week = os.environ.get("WEEK_DATE")
    run_scrape(week_date=week)
