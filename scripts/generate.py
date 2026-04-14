import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

from scripts.utils import latest_data_file, load_all_data

PROMPT_TEMPLATE = """你是一位专业IPO研究分析师。根据以下SEC招股书摘录，生成JSON格式的结构化分析。
只输出一个JSON对象，不要任何其他文字或markdown代码块。

公司：{company}（{symbol}）
交易所：{exchange}
招股书摘录（来自S-1 Business、Risk Factors、Financial Highlights三节）：
---
{sec_raw_excerpt}
---

输出以下JSON结构（字段无法提取时填null）：
{{
  "industry": "行业分类（英文）",
  "business_summary": "核心业务描述（中文，100字以内）",
  "financials": {{
    "revenue_3y": [年1数字, 年2数字, 年3数字],
    "net_income_3y": [年1数字, 年2数字, 年3数字],
    "gross_margin": "xx%或null",
    "revenue_growth_yoy": "xx%或null",
    "debt_ratio": "x.x或null",
    "cash_reserves": "$xxM或null",
    "operating_cashflow": "$xxM或null",
    "eps": "x.xx或null",
    "ps_ratio": "x.xx或null"
  }},
  "investors": {{
    "underwriters": [],
    "cornerstone_investors": [],
    "funding_rounds": []
  }},
  "risks": ["风险1", "风险2", "风险3"],
  "claude_summary": "综合评价（中文，100字以内）"
}}"""


def build_prompt(ipo: dict) -> str:
    return PROMPT_TEMPLATE.format(
        company=ipo.get("company", ""),
        symbol=ipo.get("symbol", ""),
        exchange=ipo.get("exchange", ""),
        sec_raw_excerpt=ipo.get("sec_raw_excerpt") or "（招股书摘录不可用，请根据公司名和代码推断）",
    )


def _extract_outermost_json(text: str) -> str | None:
    """Extract the first complete outermost JSON object from text using bracket counting."""
    depth = 0
    start = None
    for i, c in enumerate(text):
        if c == '{':
            if depth == 0:
                start = i
            depth += 1
        elif c == '}':
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    return text[start:i + 1]
    return None


def run_claude(prompt: str) -> dict:
    """
    Call 'claude -p' with prompt via stdin. Returns parsed dict.
    On failure returns {"error": "..."}.

    Uses shutil.which() to resolve full executable path so Windows .CMD
    wrappers (npm-installed claude.cmd) are found by subprocess.
    """
    claude_exe = shutil.which("claude")
    if not claude_exe:
        return {"error": "claude executable not found in PATH"}
    try:
        result = subprocess.run(
            [claude_exe, "-p"],
            input=prompt.encode("utf-8"),
            capture_output=True,
            timeout=120,
        )
        raw_bytes = result.stdout or b""
        # Try UTF-8 first, fall back to GBK (Windows default CJK encoding)
        for enc in ("utf-8", "gbk", "utf-8-sig"):
            try:
                output = raw_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            output = raw_bytes.decode("utf-8", errors="replace")
        json_str = _extract_outermost_json(output)
        if json_str is None:
            return {"error": "parse_failed", "raw": output[:500]}
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Remove ASCII control chars (except \t\n\r), then retry
            cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', json_str)
            return json.loads(cleaned)
    except subprocess.TimeoutExpired:
        return {"error": "timeout"}
    except json.JSONDecodeError as e:
        return {"error": f"json_decode: {e}"}
    except Exception as e:
        return {"error": str(e)}


def generate_all(data_dir: str = "data", skip_git: bool = False):
    """
    Read latest data file, generate analysis for companies with analysis=None,
    write back after each company (resumable). Then rebuild HTML and push.
    """
    if not skip_git:
        result = subprocess.run(["git", "pull", "--ff-only"], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[generate] Warning: git pull failed: {result.stderr.strip()}")

    latest = latest_data_file(data_dir)
    if not latest:
        print("[generate] No data file found.")
        return

    with open(latest, encoding="utf-8") as f:
        data = json.load(f)

    pending = [ipo for ipo in data["ipos"] if ipo.get("analysis") is None]
    print(f"[generate] {len(pending)} companies to analyze in {latest}")

    for ipo in pending:
        symbol = ipo["symbol"]
        print(f"[generate] Analyzing {symbol} ({ipo['company']})...")
        prompt = build_prompt(ipo)
        analysis = run_claude(prompt)
        ipo["analysis"] = analysis
        with open(latest, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[generate] Done {symbol}")

    data["ai_analyzed_at"] = datetime.utcnow().isoformat() + "Z"
    with open(latest, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Rebuild full HTML — call build_html directly, no sys.argv injection
    from scripts.build import build_html
    weeks = load_all_data(data_dir)
    html = build_html(weeks, mode="full")
    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("[generate] Built docs/index.html (full mode)")

    if not skip_git:
        week = data.get("week", "unknown")
        subprocess.run(["git", "add", latest, "docs/index.html"], check=True)
        subprocess.run(["git", "commit", "-m", f"feat: AI analysis {week}"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("[generate] Pushed. View at https://dgsirius.github.io/ipo-monitor")


if __name__ == "__main__":
    generate_all()
