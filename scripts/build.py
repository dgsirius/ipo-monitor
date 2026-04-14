import argparse
import json
import os
import sys

from scripts.utils import load_all_data

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IPO Monitor</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f5f5f5; color: #333; }
header { background: #1a1a2e; color: #fff; padding: 12px 20px; display: flex; align-items: center; gap: 12px; position: sticky; top: 0; z-index: 100; }
header h1 { font-size: 18px; font-weight: 700; }
.badge { padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
.badge.basic { background: #e67e22; color: #fff; }
.badge.full { background: #27ae60; color: #fff; }
#search { margin-left: auto; padding: 6px 12px; border-radius: 6px; border: none; font-size: 14px; width: 240px; }
.layout { display: flex; height: calc(100vh - 48px); }
#sidebar { width: 200px; min-width: 200px; background: #fff; border-right: 1px solid #e0e0e0; overflow-y: auto; padding: 8px 0; }
.week-header { padding: 8px 12px; font-size: 12px; font-weight: 700; color: #666; cursor: pointer; user-select: none; display: flex; justify-content: space-between; }
.week-header:hover { background: #f0f0f0; }
.week-companies { display: none; }
.week-companies.open { display: block; }
.sidebar-company { padding: 5px 16px; font-size: 12px; cursor: pointer; color: #1a73e8; line-height: 1.4; }
.sidebar-company:hover { background: #e8f0fe; }
.sidebar-company .sym { font-weight: 700; }
.sidebar-company .co { color: #888; font-size: 11px; display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
#gen-btn { display: none; margin-left: 8px; padding: 6px 14px; background: #27ae60; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600; white-space: nowrap; }
#gen-btn:disabled { background: #888; cursor: not-allowed; }
#gen-log { display: none; position: fixed; bottom: 0; left: 0; right: 0; background: #1a1a2e; color: #aef; font-size: 12px; padding: 8px 16px; max-height: 120px; overflow-y: auto; z-index: 200; white-space: pre-wrap; }
#content { flex: 1; overflow-y: auto; padding: 16px; }
.card { background: #fff; border-radius: 8px; border: 1px solid #e0e0e0; padding: 16px; margin-bottom: 12px; scroll-margin-top: 16px; }
.card.highlight { border-color: #1a73e8; box-shadow: 0 0 0 2px #e8f0fe; }
.card-title { font-size: 16px; font-weight: 700; }
.card-title .symbol { color: #1a73e8; margin-right: 8px; }
.card-meta { font-size: 13px; color: #666; margin-top: 4px; }
.tag { display: inline-block; background: #e8f0fe; color: #1a73e8; border-radius: 4px; padding: 2px 8px; font-size: 12px; margin: 2px; }
.tag.exchange { background: #fce8e6; color: #c0392b; }
.collapsible { margin-top: 10px; border-top: 1px solid #f0f0f0; padding-top: 8px; }
.collapsible-header { cursor: pointer; font-size: 13px; font-weight: 600; color: #555; user-select: none; padding: 4px 0; }
.collapsible-header::before { content: "▶ "; font-size: 10px; }
.collapsible-header.open::before { content: "▼ "; }
.collapsible-body { display: none; padding: 8px 0 4px 12px; font-size: 13px; color: #444; }
.collapsible-body.open { display: block; }
.fin-row { display: flex; gap: 16px; flex-wrap: wrap; margin: 4px 0; }
.fin-item { min-width: 120px; }
.fin-label { font-size: 11px; color: #888; }
.fin-value { font-size: 14px; font-weight: 600; }
.pending { color: #aaa; font-style: italic; }
footer { text-align: center; padding: 12px; font-size: 12px; color: #888; border-top: 1px solid #e0e0e0; background: #fff; }
.hidden { display: none !important; }
</style>
</head>
<body>
<header>
  <h1>IPO Monitor</h1>
  <span class="badge {BADGE_CLASS}" id="version-badge">{BADGE_TEXT}</span>
  <button id="gen-btn" onclick="runGenerate()">🤖 生成完整版</button>
  <input type="text" id="search" placeholder="搜索公司代码或名称...">
</header>
<div class="layout">
  <nav id="sidebar"></nav>
  <main id="content"></main>
</div>
<footer>
  数据来源：stockanalysis.com · SEC EDGAR &nbsp;|&nbsp;
  基础版更新：<span id="basic-ts">{BASIC_TS}</span>
  <span id="ai-ts-wrap">&nbsp;|&nbsp; AI分析更新：<span id="ai-ts">{AI_TS}</span></span>
</footer>
<div id="gen-log"></div>
<script>
const DATA = {DATA_JSON};

function esc(s) {
  if (s == null) return "—";
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

function collapsible(title, bodyHtml) {
  return '<div class="collapsible"><div class="collapsible-header open" onclick="toggleSection(this)">' + title + '</div><div class="collapsible-body open">' + bodyHtml + '</div></div>';
}

function fmt3y(arr) {
  if (!Array.isArray(arr)) return "—";
  return arr.map(function(v) { return v == null ? "—" : v; }).join(" → ");
}
function buildFinancials(ipo) {
  if (!ipo.analysis) return collapsible("基本面", '<span class="pending">AI 分析待生成</span>');
  var f = ipo.analysis.financials || {};
  var rev = fmt3y(f.revenue_3y);
  var ni = fmt3y(f.net_income_3y);
  return collapsible("基本面", '<div class="fin-row">' +
    '<div class="fin-item"><div class="fin-label">收入趋势(3Y)</div><div class="fin-value">' + esc(rev) + '</div></div>' +
    '<div class="fin-item"><div class="fin-label">净利润趋势(3Y)</div><div class="fin-value">' + esc(ni) + '</div></div>' +
    '<div class="fin-item"><div class="fin-label">毛利率</div><div class="fin-value">' + esc(f.gross_margin) + '</div></div>' +
    '<div class="fin-item"><div class="fin-label">YoY增速</div><div class="fin-value">' + esc(f.revenue_growth_yoy) + '</div></div>' +
    '<div class="fin-item"><div class="fin-label">现金储备</div><div class="fin-value">' + esc(f.cash_reserves) + '</div></div>' +
    '<div class="fin-item"><div class="fin-label">负债率</div><div class="fin-value">' + esc(f.debt_ratio) + '</div></div>' +
    '<div class="fin-item"><div class="fin-label">经营现金流</div><div class="fin-value">' + esc(f.operating_cashflow) + '</div></div>' +
    '<div class="fin-item"><div class="fin-label">EPS</div><div class="fin-value">' + esc(f.eps) + '</div></div>' +
    '<div class="fin-item"><div class="fin-label">P/S</div><div class="fin-value">' + esc(f.ps_ratio) + '</div></div>' +
    '</div>');
}

function buildFunding(ipo) {
  if (!ipo.analysis) return collapsible("融资历史", '<span class="pending">AI 分析待生成</span>');
  var inv = ipo.analysis.investors || {};
  var rounds = (inv.funding_rounds || []).map(function(r) {
    return '<div>' + esc(r.round) + ' ' + esc(r.amount) + ' · ' + (r.investors || []).map(esc).join(", ") + '</div>';
  }).join("");
  return collapsible("融资历史", rounds || '<span class="pending">暂无数据</span>');
}

function buildSummary(ipo) {
  if (!ipo.analysis || !ipo.analysis.claude_summary)
    return collapsible("Claude 分析摘要", '<span class="pending">AI 分析待生成</span>');
  var risks = (ipo.analysis.risks || []).map(function(r) { return '<li>' + esc(r) + '</li>'; }).join("");
  return collapsible("Claude 分析摘要",
    '<p><strong>业务：</strong>' + esc(ipo.analysis.business_summary) + '</p>' +
    '<p style="margin-top:6px"><strong>风险：</strong></p>' +
    '<ul style="padding-left:16px">' + risks + '</ul>' +
    '<p style="margin-top:6px"><strong>综合评价：</strong>' + esc(ipo.analysis.claude_summary) + '</p>');
}

function toggleSection(header) {
  header.classList.toggle("open");
  header.nextElementSibling.classList.toggle("open");
}

function scrollToCard(symbol) {
  document.querySelectorAll(".card").forEach(function(c) { c.classList.remove("highlight"); });
  var card = document.getElementById("card-" + symbol);
  if (card) { card.classList.add("highlight"); card.scrollIntoView({ behavior: "smooth", block: "start" }); }
}

// Build sidebar — one entry per week, all tickers sorted by IPO date
var sidebar = document.getElementById("sidebar");
DATA.forEach(function(week) {
  var sorted = week.ipos.slice().sort(function(a, b) {
    return a.ipo_date < b.ipo_date ? -1 : a.ipo_date > b.ipo_date ? 1 : 0;
  });
  var label = week.week || sorted[0].ipo_date.slice(0, 7);
  var header = document.createElement("div");
  header.className = "week-header";
  header.innerHTML = '<span>📅 ' + label + ' 本周</span><span class="toggle-arrow">▾</span>';
  var companies = document.createElement("div");
  companies.className = "week-companies open";
  sorted.forEach(function(ipo) {
    var a = document.createElement("div");
    a.className = "sidebar-company";
    a.innerHTML = '<span class="sym">' + esc(ipo.symbol) + '</span>'
      + '<span class="co">' + esc(ipo.ipo_date.slice(5)) + ' ' + esc(ipo.company) + '</span>';
    a.addEventListener("click", function() { scrollToCard(ipo.symbol); });
    companies.appendChild(a);
  });
  header.addEventListener("click", function() {
    companies.classList.toggle("open");
    header.querySelector(".toggle-arrow").textContent = companies.classList.contains("open") ? "▾" : "▸";
  });
  sidebar.appendChild(header);
  sidebar.appendChild(companies);
});

// Build cards
var content = document.getElementById("content");
DATA.forEach(function(week) {
  week.ipos.forEach(function(ipo) {
    var card = document.createElement("div");
    card.className = "card";
    card.id = "card-" + ipo.symbol;
    var an = ipo.analysis;
    var industry = an ? '<span class="tag">' + esc(an.industry || "") + '</span>' : "";
    var underwriters = an && an.investors && an.investors.underwriters && an.investors.underwriters.length
      ? '<span class="tag">承销：' + an.investors.underwriters.map(esc).join(" / ") + '</span>' : "";
    card.innerHTML =
      '<div class="card-title"><span class="symbol">' + esc(ipo.symbol) + '</span>· ' + esc(ipo.company) + '</div>' +
      '<div class="card-meta"><span class="tag exchange">' + esc(ipo.exchange) + '</span> ' +
      esc(ipo.ipo_date) + ' &nbsp;|&nbsp; 发行价 ' + esc(ipo.price_range) + ' · 规模 ' + esc(ipo.deal_size) + ' · 市值 ' + esc(ipo.market_cap) + '</div>' +
      '<div style="margin-top:6px">' + industry + underwriters + '</div>' +
      buildFinancials(ipo) + buildFunding(ipo) + buildSummary(ipo);
    content.appendChild(card);
  });
});

// Local-only generate button
if (location.hostname === "localhost" || location.hostname === "127.0.0.1") {
  document.getElementById("gen-btn").style.display = "inline-block";
}

function runGenerate() {
  var btn = document.getElementById("gen-btn");
  var log = document.getElementById("gen-log");
  btn.disabled = true;
  btn.textContent = "⏳ 生成中...";
  log.style.display = "block";
  log.textContent = "正在启动 generate.py...";
  fetch("/run-generate", {method: "POST"})
    .then(function(r) { return r.json(); })
    .then(function() { pollStatus(); })
    .catch(function(e) { log.textContent = "错误: " + e; btn.disabled = false; btn.textContent = "🤖 生成完整版"; });
}

function pollStatus() {
  fetch("/status").then(function(r) { return r.json(); }).then(function(d) {
    var log = document.getElementById("gen-log");
    if (d.log) { log.textContent = d.log; log.scrollTop = log.scrollHeight; }
    if (d.running) {
      setTimeout(pollStatus, 2000);
    } else {
      document.getElementById("gen-btn").textContent = "✅ 完成，刷新中...";
      setTimeout(function() { location.reload(); }, 1500);
    }
  });
}

// Search
document.getElementById("search").addEventListener("input", function() {
  var q = this.value.toLowerCase().trim();
  document.querySelectorAll(".card").forEach(function(card) {
    card.classList.toggle("hidden", q !== "" && !card.textContent.toLowerCase().includes(q));
  });
  document.querySelectorAll(".sidebar-company").forEach(function(a) {
    var text = (a.querySelector(".sym") ? a.querySelector(".sym").textContent : a.textContent).toLowerCase();
    var co = (a.querySelector(".co") ? a.querySelector(".co").textContent : "").toLowerCase();
    a.classList.toggle("hidden", q !== "" && !text.includes(q) && !co.includes(q));
  });
});
</script>
</body>
</html>
"""


def build_html(weeks: list, mode: str = "basic") -> str:
    """Build index.html from list of week dicts. mode: 'basic' or 'full'."""
    has_ai = any(w.get("ai_analyzed_at") for w in weeks)
    badge_class = "full" if has_ai else "basic"
    badge_text = "完整版" if has_ai else "基础版"

    basic_ts = weeks[0].get("generated_at", "—")[:16].replace("T", " ") if weeks else "—"
    ai_ts = ""
    for w in weeks:
        if w.get("ai_analyzed_at"):
            ai_ts = w["ai_analyzed_at"][:16].replace("T", " ")
            break

    data_json = json.dumps(weeks, ensure_ascii=False).replace("</", "<\\/")
    html = HTML_TEMPLATE
    html = html.replace("{BADGE_CLASS}", badge_class)
    html = html.replace("{BADGE_TEXT}", badge_text)
    html = html.replace("{BASIC_TS}", basic_ts)
    html = html.replace("{AI_TS}", ai_ts if ai_ts else "—")
    html = html.replace("{DATA_JSON}", data_json)
    return html


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["basic", "full"], default="basic")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--out", default="docs/index.html")
    args = parser.parse_args()

    weeks = load_all_data(args.data_dir)
    if not weeks:
        print("[build] No data files found, writing empty page")
        weeks = []

    html = build_html(weeks, mode=args.mode)
    os.makedirs(os.path.dirname(args.out) if os.path.dirname(args.out) else ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[build] Written {args.out} ({len(weeks)} weeks, mode={args.mode})")


if __name__ == "__main__":
    main()
