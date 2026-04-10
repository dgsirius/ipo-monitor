import json
import pytest

SAMPLE_IPO = {
    "symbol": "TEST",
    "company": "Test Corp",
    "ipo_date": "2026-04-15",
    "exchange": "NASDAQ",
    "price_range": "$10-12",
    "shares_offered": "5,000,000",
    "deal_size": "$55M",
    "market_cap": "$300M",
    "revenue": "$50M",
    "sec_filing_url": "https://www.sec.gov/Archives/edgar/data/99999/000009999926000001/test-s1.htm",
    "sec_raw_excerpt": "BUSINESS: Test Corp provides software. RISK FACTORS: Competition risk. FINANCIAL: Revenue $50M.",
    "analysis": None
}

SAMPLE_WEEK = {
    "week": "2026-04-13",
    "generated_at": "2026-04-13T06:00:00Z",
    "ai_analyzed_at": None,
    "ipo_count": 1,
    "ipos": [SAMPLE_IPO]
}

@pytest.fixture
def sample_week():
    return json.loads(json.dumps(SAMPLE_WEEK))  # deep copy

@pytest.fixture
def sample_ipo():
    return json.loads(json.dumps(SAMPLE_IPO))
