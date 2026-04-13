# tests/test_build.py
import json
import pytest
from scripts.build import build_html

WEEK_WITH_ANALYSIS = {
    "week": "2026-04-13",
    "generated_at": "2026-04-13T06:00:00Z",
    "ai_analyzed_at": "2026-04-13T08:30:00Z",
    "ipo_count": 1,
    "ipos": [{
        "symbol": "ABCD",
        "company": "Acme Corp",
        "ipo_date": "2026-04-15",
        "exchange": "NASDAQ",
        "price_range": "$14-16",
        "shares_offered": "10,000,000",
        "deal_size": "$150M",
        "market_cap": "$800M",
        "revenue": "$120M",
        "sec_filing_url": "https://sec.gov/test.htm",
        "sec_raw_excerpt": "Business text here.",
        "analysis": {
            "industry": "Cloud SaaS",
            "business_summary": "提供云软件解决方案",
            "financials": {
                "revenue_3y": [30, 40, 50],
                "net_income_3y": [-10, -7, -5],
                "gross_margin": "72%",
                "revenue_growth_yoy": "25%",
                "debt_ratio": "0.3",
                "cash_reserves": "$45M",
                "operating_cashflow": "-$8M",
                "eps": "-0.12",
                "ps_ratio": "6.0x"
            },
            "investors": {
                "underwriters": ["Goldman Sachs"],
                "cornerstone_investors": [],
                "funding_rounds": [
                    {"round": "Series B", "amount": "$30M", "investors": ["a16z"]}
                ]
            },
            "risks": ["竞争风险", "亏损历史", "客户集中"],
            "claude_summary": "综合评价：增长强劲但持续亏损"
        }
    }]
}

WEEK_BASIC = {
    "week": "2026-04-13",
    "generated_at": "2026-04-13T06:00:00Z",
    "ai_analyzed_at": None,
    "ipo_count": 1,
    "ipos": [{
        "symbol": "EFGH",
        "company": "Beta Inc",
        "ipo_date": "2026-04-22",
        "exchange": "NYSE",
        "price_range": "$20-22",
        "shares_offered": "8,000,000",
        "deal_size": "$168M",
        "market_cap": "$600M",
        "revenue": "$80M",
        "sec_filing_url": None,
        "sec_raw_excerpt": None,
        "analysis": None
    }]
}


def test_build_html_contains_company_name():
    html = build_html([WEEK_WITH_ANALYSIS], mode="full")
    assert "Acme Corp" in html
    assert "ABCD" in html


def test_build_html_basic_mode_shows_placeholder():
    html = build_html([WEEK_BASIC], mode="basic")
    assert "EFGH" in html
    assert "分析待生成" in html or "AI" in html


def test_build_html_full_mode_shows_analysis():
    html = build_html([WEEK_WITH_ANALYSIS], mode="full")
    assert "Cloud SaaS" in html
    assert "Goldman Sachs" in html
    assert "综合评价" in html


def test_build_html_inlines_data():
    html = build_html([WEEK_WITH_ANALYSIS], mode="full")
    assert "const DATA" in html
    assert "2026-04-13" in html


def test_build_html_shows_version_badge_full():
    html = build_html([WEEK_WITH_ANALYSIS], mode="full")
    assert "完整版" in html


def test_build_html_shows_version_badge_basic():
    html = build_html([WEEK_BASIC], mode="basic")
    assert "基础版" in html
