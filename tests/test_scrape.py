# tests/test_scrape.py
from unittest.mock import patch, MagicMock
from scripts.scrape import parse_ipo_calendar

MOCK_HTML = """
<html><body>
<h2>This Week</h2>
<table>
<thead><tr>
  <th>IPO Date</th><th>Symbol</th><th>Company Name</th>
  <th>Exchange</th><th>Price Range</th><th>Shares Offered</th>
  <th>Deal Size</th><th>Market Cap</th><th>Revenue</th>
</tr></thead>
<tbody>
<tr>
  <td>Apr 15, 2026</td><td>ABCD</td><td>Acme Corp</td>
  <td>NASDAQ</td><td>$14-16</td><td>10,000,000</td>
  <td>$150M</td><td>$800M</td><td>$120M</td>
</tr>
</tbody>
</table>
<h2>Next Week</h2>
<table>
<thead><tr>
  <th>IPO Date</th><th>Symbol</th><th>Company Name</th>
  <th>Exchange</th><th>Price Range</th><th>Shares Offered</th>
  <th>Deal Size</th><th>Market Cap</th><th>Revenue</th>
</tr></thead>
<tbody>
<tr>
  <td>Apr 22, 2026</td><td>EFGH</td><td>Beta Inc</td>
  <td>NYSE</td><td>$20-22</td><td>8,000,000</td>
  <td>$168M</td><td>$600M</td><td>$80M</td>
</tr>
</tbody>
</table>
</body></html>
"""


def test_parse_ipo_calendar_returns_both_weeks():
    with patch("scripts.scrape.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.text = MOCK_HTML
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        ipos = parse_ipo_calendar()

    assert len(ipos) == 2
    symbols = [ipo["symbol"] for ipo in ipos]
    assert "ABCD" in symbols
    assert "EFGH" in symbols


def test_parse_ipo_calendar_fields():
    with patch("scripts.scrape.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.text = MOCK_HTML
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        ipos = parse_ipo_calendar()

    abcd = next(i for i in ipos if i["symbol"] == "ABCD")
    assert abcd["company"] == "Acme Corp"
    assert abcd["exchange"] == "NASDAQ"
    assert abcd["price_range"] == "$14-16"
    assert abcd["ipo_date"] == "2026-04-15"


from scripts.scrape import search_edgar, fetch_s1_excerpt

MOCK_EDGAR_RESPONSE = {
    "hits": {
        "hits": [
            {
                "_source": {
                    "entity_id": "99999",
                    "file_date": "2026-03-01",
                    "form_type": "S-1",
                    "accession_no": "0000999999-26-000001",
                    "display_names": ["Test Corp (CIK 0000099999)"]
                }
            }
        ],
        "total": {"value": 1}
    }
}

MOCK_FILING_INDEX = """
<html><body>
<table><tr><td><a href="/Archives/edgar/data/99999/000009999926000001/test-s1.htm">test-s1.htm</a></td><td>S-1</td><td>100000</td></tr></table>
</body></html>
"""

MOCK_S1_HTML = """
<html><body>
<h2>BUSINESS</h2>
<p>Test Corp provides cloud software solutions to enterprise customers.
We help businesses automate workflows and reduce costs through our platform.
Our revenue grew 25% year over year to $50 million in fiscal 2025.</p>
<h2>RISK FACTORS</h2>
<p>Competition from larger companies may harm our business.
We have a history of net losses and may not achieve profitability.
Our revenue is concentrated among a small number of customers.</p>
<h2>RESULTS OF OPERATIONS</h2>
<p>Revenue for fiscal year 2025 was $50.0 million, compared to $40.0 million
in 2024 and $30.0 million in 2023. Gross margin was 72%.
Net loss was $5.2 million in 2025.</p>
</body></html>
"""


def test_search_edgar_returns_filing_url():
    with patch("scripts.scrape.requests.get") as mock_get:
        edgar_resp = MagicMock()
        edgar_resp.json.return_value = MOCK_EDGAR_RESPONSE
        edgar_resp.raise_for_status = MagicMock()
        index_resp = MagicMock()
        index_resp.text = MOCK_FILING_INDEX
        index_resp.raise_for_status = MagicMock()
        mock_get.side_effect = [edgar_resp, index_resp]

        url = search_edgar("TEST", "Test Corp")

    assert url is not None
    assert "sec.gov" in url


def test_search_edgar_returns_none_on_no_results():
    with patch("scripts.scrape.requests.get") as mock_get:
        empty_resp = MagicMock()
        empty_resp.json.return_value = {"hits": {"hits": [], "total": {"value": 0}}}
        empty_resp.raise_for_status = MagicMock()
        mock_get.return_value = empty_resp

        url = search_edgar("ZZZNONE", "Unknown Corp")

    assert url is None


def test_fetch_s1_excerpt_extracts_three_sections():
    with patch("scripts.scrape.requests.get") as mock_get:
        s1_resp = MagicMock()
        s1_resp.text = MOCK_S1_HTML
        s1_resp.raise_for_status = MagicMock()
        mock_get.return_value = s1_resp

        excerpt = fetch_s1_excerpt("https://www.sec.gov/Archives/edgar/data/99999/test-s1.htm")

    assert "BUSINESS" in excerpt or "cloud software" in excerpt.lower()
    assert "RISK" in excerpt or "competition" in excerpt.lower()
    assert len(excerpt) <= 3000


def test_fetch_s1_excerpt_returns_empty_on_failure():
    with patch("scripts.scrape.requests.get") as mock_get:
        mock_get.side_effect = Exception("network error")

        excerpt = fetch_s1_excerpt("https://www.sec.gov/bogus.htm")

    assert excerpt == ""


import json
import tempfile
from pathlib import Path
from scripts.scrape import run_scrape


def test_run_scrape_creates_json(tmp_path):
    ipos = [
        {
            "symbol": "ABCD", "company": "Acme Corp", "ipo_date": "2026-04-15",
            "exchange": "NASDAQ", "price_range": "$14-16", "shares_offered": "10M",
            "deal_size": "$150M", "market_cap": "$800M", "revenue": "$120M",
            "sec_filing_url": None, "sec_raw_excerpt": None, "analysis": None
        }
    ]
    with patch("scripts.scrape.parse_ipo_calendar", return_value=ipos), \
         patch("scripts.scrape.search_edgar", return_value="https://sec.gov/test.htm"), \
         patch("scripts.scrape.fetch_s1_excerpt", return_value="Business excerpt"):

        output_path = run_scrape(data_dir=str(tmp_path), week_date="2026-04-13")

    assert output_path.endswith("2026-04-13.json")
    data = json.loads(Path(output_path).read_text())
    assert data["week"] == "2026-04-13"
    assert data["ipo_count"] == 1
    assert data["ipos"][0]["symbol"] == "ABCD"
    assert data["ipos"][0]["sec_raw_excerpt"] == "Business excerpt"
    assert data["ipos"][0]["analysis"] is None
