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
