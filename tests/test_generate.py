# tests/test_generate.py
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from scripts.generate import run_claude, build_prompt, generate_all

MOCK_CLAUDE_OUTPUT = json.dumps({
    "industry": "Cloud SaaS",
    "business_summary": "提供云软件解决方案给企业客户",
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
        "funding_rounds": [{"round": "Series B", "amount": "$30M", "investors": ["a16z"]}]
    },
    "risks": ["竞争风险", "亏损历史", "客户集中"],
    "claude_summary": "增长强劲但持续亏损，需关注盈利路径"
})


def test_build_prompt_contains_company():
    ipo = {
        "symbol": "TEST", "company": "Test Corp", "exchange": "NASDAQ",
        "sec_raw_excerpt": "Business description here."
    }
    prompt = build_prompt(ipo)
    assert "TEST" in prompt
    assert "Test Corp" in prompt
    assert "Business description here." in prompt


def test_run_claude_returns_parsed_json():
    with patch("scripts.generate.subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.stdout = MOCK_CLAUDE_OUTPUT
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        result = run_claude("test prompt")

    assert result["industry"] == "Cloud SaaS"
    assert result["financials"]["gross_margin"] == "72%"


def test_run_claude_handles_extra_text():
    """Claude sometimes adds preamble before JSON."""
    with patch("scripts.generate.subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.stdout = "Here is the analysis:\n" + MOCK_CLAUDE_OUTPUT + "\nDone."
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        result = run_claude("test prompt")

    assert result["industry"] == "Cloud SaaS"


def test_run_claude_returns_error_on_timeout():
    import subprocess
    with patch("scripts.generate.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(["claude"], 120)

        result = run_claude("test prompt")

    assert "error" in result
    assert "timeout" in result["error"]


def test_generate_all_fills_analysis(tmp_path, sample_week):
    data_file = tmp_path / "2026-04-13.json"
    data_file.write_text(json.dumps(sample_week))

    with patch("scripts.generate.run_claude", return_value=json.loads(MOCK_CLAUDE_OUTPUT)):
        generate_all(data_dir=str(tmp_path), skip_git=True)

    updated = json.loads(data_file.read_text(encoding="utf-8"))
    assert updated["ipos"][0]["analysis"] is not None
    assert updated["ai_analyzed_at"] is not None


def test_generate_all_skips_already_analyzed(tmp_path):
    week = {
        "week": "2026-04-13", "generated_at": "2026-04-13T06:00:00Z",
        "ai_analyzed_at": None, "ipo_count": 1,
        "ipos": [{
            "symbol": "DONE", "company": "Done Corp", "ipo_date": "2026-04-15",
            "exchange": "NASDAQ", "price_range": "$10-12",
            "shares_offered": "1M", "deal_size": "$11M", "market_cap": "$100M",
            "revenue": "$20M", "sec_filing_url": None, "sec_raw_excerpt": None,
            "analysis": {"industry": "Already done", "business_summary": "x",
                         "financials": {}, "investors": {}, "risks": [], "claude_summary": "y"}
        }]
    }
    data_file = tmp_path / "2026-04-13.json"
    data_file.write_text(json.dumps(week))

    call_count = {"n": 0}
    def mock_claude(prompt):
        call_count["n"] += 1
        return {}

    with patch("scripts.generate.run_claude", side_effect=mock_claude):
        generate_all(data_dir=str(tmp_path), skip_git=True)

    assert call_count["n"] == 0
