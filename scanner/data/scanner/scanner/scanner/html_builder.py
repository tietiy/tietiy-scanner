import os
import sys
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))
from config import OUTPUT_DIR

def get_action_color(action):
    if action == 'DEPLOY':  return '#00C851'
    if action == 'WATCH':   return '#FFD700'
    if action == 'CAUTION': return '#FF8800'
    return '#FF4444'

def get_regime_color(regime):
    if regime == 'Bear':   return '#FF4444'
    if regime == 'Bull':   return '#00C851'
    return '#FFD700'

def get_health_emoji(health):
    if health == 'HOT':    return '🟢'
    if health == 'COLD':   return '🔴'
    return '🟡'

def build_sector_heatmap(sector_momentum):
    icons = {
        'Leading': '🟢', 'Neutral': '🟡', 'Lagging': '🔴'
    }
    cells = ''
    for sec, mom in sector_momentum.items():
        icon = icons.get(mom, '🟡')
        cells += (
            f'<div class="sector-cell">'
            f'{icon} {sec}</div>'
        )
    return f'<div class="sector-grid">{cells}</div>'

def build_signal_card(sig):
    action     = sig.get('action','')
    score      = sig.get('score', 0)
    signal     = sig.get('signal','')
    symbol     = sig.get('symbol','').replace('.NS','')
    sector     = sig.get('sector','')
    age        = sig.get('age', 0)
    regime     = sig.get('regime','')
    vol_q      = sig.get('vol_q','')
    rs_q       = sig.get('rs_q','')
    sec_mom    = sig.get('sec_mom','')
    entry      = sig.get('entry_est', 0)
    stop       = sig.get('stop', 0)
    target     = sig.get('target', None)
    rr         = sig.get('rr', None)
    shares     = sig.get('shares', 0)
    risk       = sig.get('risk_amt', 0)
    ex_date    = sig.get('exit_date','')
    ex_rule    = sig.get('exit_rule','')
    bear_b     = sig.get('bear_bonus', False)
    grade      = sig.get('grade','B')
    breakdown  = sig.get('breakdown','')
    exp_warn   = sig.get('expiry_warn', False)
    entry_date = sig.get('entry_date','')

    ac = get_action_color(action)
    rc = get_regime_color(regime)

    arrow = '▲' if signal in ('UP_TRI','BULL_PROXY') else '▼'
    bear_tag = '<span class="bear-tag">🐻 BEAR BONUS</span>' if bear_b else ''
    grade_tag = '<span class="grade-a">⭐ GRADE A</span>' if grade=='A' else ''
    exp_tag = '<div class="expiry-warn">⚠️ Expiry week — consider reducing size</div>' if exp_warn else ''

    target_html = (
        f'<div class="sig-row">'
        f'<span class="label">Target</span>'
        f'<span class="value green">₹{target:,.2f}</span>'
        f'<span class="label ml">R:R</span>'
        f'<span class="value">{rr}</span></div>'
        if target else
        f'<div class="sig-row">'
        f'<span class="label">Exit</span>'
        f'<span class="value">{ex_date} open ({ex_rule})</span></div>'
    )

    card = f'''
<div class="signal-card" data-signal="{signal}"
     data-action="{action}" data-age="{age}"
     data-grade="{grade}">
  <div class="card-header" style="border-left:4px solid {ac}">
    <div class="card-title">
      <span class="stock-name">{symbol}</span>
      <span class="signal-badge">{signal} {arrow}</span>
      {bear_tag}{grade_tag}
    </div>
    <div class="action-badge" style="background:{ac}">
      {action} {score}/10
    </div>
  </div>
  <div class="card-body">
    <div class="sig-row">
      <span class="label">Sector</span>
      <span class="value">{sector}</span>
      <span class="label ml">Age</span>
      <span class="value">{age}</span>
    </div>
    <div class="sig-row">
      <span class="label">Regime</span>
      <span class="value" style="color:{rc}">{regime}</span>
      <span class="label ml">Vol</span>
      <span class="value">{vol_q}</span>
      <span class="label ml">RS</span>
      <span class="value">{rs_q}</span>
    </div>
    <div class="sig-row entry-row">
      <span class="label">Entry</span>
      <span class="value green">~₹{entry:,.2f}</span>
      <span class="entry-note">({entry_date} 9:15 open)</span>
    </div>
    <div class="sig-row">
      <span class="label">Stop</span>
      <span class="value red">₹{stop:,.2f}</span>
    </div>
    {target_html}
    <div class="sig-row">
      <span class="label">Size</span>
      <span class="value">{shares} shares</span>
      <span class="label ml">Risk</span>
      <span class="value">₹{risk:,.0f}</span>
    </div>
    <div class="breakdown">{breakdown}</div>
    {exp_tag}
  </div>
</div>'''
    return card

def build_journal_row(trade):
    stock  = trade['stock'].replace('.NS','')
    signal = trade['signal_type']
    status = trade['status']
    entry  = trade.get('entry_actual') or trade.get('entry_estimate','—')
    stop   = trade.get('stop_price','—')
    pnl    = trade.get('pnl_pct','—')
    ex_dt  = trade.get('exit_date_plan','—')

    if status == 'WON':
        sc = '#00C851'; emoji = '✅'
    elif status in ('STOPPED','EXITED') and str(pnl).startswith('-'):
        sc = '#FF4444'; emoji = '❌'
    elif status == 'OPEN':
        sc = '#FFD700'; emoji = '📊'
    else:
        sc = '#888'; emoji = '⏳'

    pnl_str = f"{pnl}%" if pnl and pnl != '—' else '—'

    return f'''
<tr style="border-left:3px solid {sc}">
  <td>{emoji} {stock}</td>
  <td>{signal}</td>
  <td>₹{entry}</td>
  <td>₹{stop}</td>
  <td>{ex_dt}</td>
  <td style="color:{sc};font-weight:bold">{pnl_str}</td>
  <td style="color:{sc}">{status}</td>
</tr>'''

def build_html(signals, market_info, sector_momentum,
               open_trades, recent_trades, system_health):
    today      = market_info.get('today','')
    regime     = market_info.get('regime','')
    reg_score  = market_info.get('regime_score', 0)
    nifty_px   = market_info.get('nifty_price', 0)
    nifty_chg  = market_info.get('nifty_change', 0)
    updated_at = datetime.now().strftime('%d %b %Y %I:%M %p')
    health     = system_health.get('health','NORMAL')
    health_wr  = system_health.get('health_wr', 0)
    h_emoji    = get_health_emoji(health)
    rc         = get_regime_color(regime)
    n_arrow    = '▲' if nifty_chg >= 0 else '▼'
    n_color    = '#00C851' if nifty_chg >= 0 else '#FF4444'
    bear_banner = (
        '<div class="bear-banner">'
        '🐻 BEAR BONUS ACTIVE — UP_TRI at highest conviction'
        '</div>'
    ) if regime == 'Bear' else ''

    signal_cards = ''.join(build_signal_card(s) for s in signals) if signals else '<div class="no-signals">📭 No signals today</div>'
    journal_rows = ''.join(build_journal_row(t) for t in (open_trades + recent_trades))

    heatmap = build_sector_heatmap(sector_momentum)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TIE TIY Scanner</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0d1117;color:#e6edf3;font-family:-apple-system,sans-serif;font-size:14px}}
.topbar{{background:#161b22;padding:10px 16px;position:sticky;top:0;z-index:100;border-bottom:1px solid #30363d}}
.topbar-row1{{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px}}
.logo{{font-weight:700;font-size:16px;color:#58a6ff}}
.nifty-price{{font-size:15px;font-weight:600}}
.updated{{font-size:11px;color:#8b949e}}
.regime-badge{{padding:3px 8px;border-radius:12px;font-size:12px;font-weight:600;color:#0d1117}}
.topbar-row2{{display:flex;gap:12px;margin-top:6px;font-size:12px;flex-wrap:wrap}}
.bear-banner{{background:#3d1f1f;border:1px solid #FF4444;color:#FF8888;padding:8px 16px;text-align:center;font-size:13px;font-weight:600}}
.sector-grid{{display:flex;flex-wrap:wrap;gap:6px;padding:10px 16px;background:#161b22;border-bottom:1px solid #30363d}}
.sector-cell{{background:#21262d;padding:4px 8px;border-radius:8px;font-size:12px}}
.filter-bar{{display:flex;gap:8px;padding:10px 16px;overflow-x:auto;background:#0d1117;border-bottom:1px solid #30363d}}
.filter-btn{{background:#21262d;border:1px solid #30363d;color:#e6edf3;padding:6px 12px;border-radius:16px;font-size:12px;cursor:pointer;white-space:nowrap}}
.filter-btn.active{{background:#58a6ff;color:#0d1117;border-color:#58a6ff}}
.signals-container{{padding:12px 16px;display:flex;flex-direction:column;gap:12px}}
.signal-card{{background:#161b22;border-radius:10px;overflow:hidden;border:1px solid #30363d}}
.card-header{{display:flex;justify-content:space-between;align-items:center;padding:10px 12px;background:#21262d}}
.card-title{{display:flex;flex-direction:column;gap:4px}}
.stock-name{{font-size:18px;font-weight:700;color:#58a6ff}}
.signal-badge{{font-size:12px;color:#8b949e}}
.bear-tag{{background:#3d1f1f;color:#FF8888;padding:2px 6px;border-radius:8px;font-size:11px}}
.grade-a{{background:#1f3d1f;color:#88FF88;padding:2px 6px;border-radius:8px;font-size:11px}}
.action-badge{{padding:4px 10px;border-radius:12px;font-size:13px;font-weight:700;color:#0d1117}}
.card-body{{padding:10px 12px;display:flex;flex-direction:column;gap:6px}}
.sig-row{{display:flex;align-items:center;gap:6px;flex-wrap:wrap}}
.label{{color:#8b949e;font-size:12px}}
.value{{font-weight:500}}
.ml{{margin-left:8px}}
.green{{color:#00C851}}
.red{{color:#FF4444}}
.entry-row{{background:#1c2128;padding:6px 8px;border-radius:6px}}
.entry-note{{font-size:11px;color:#8b949e}}
.breakdown{{font-size:11px;color:#8b949e;margin-top:4px;padding-top:4px;border-top:1px solid #30363d}}
.expiry-warn{{background:#2d2000;color:#FFD700;padding:4px 8px;border-radius:6px;font-size:11px;margin-top:4px}}
.no-signals{{text-align:center;padding:40px;color:#8b949e;font-size:16px}}
.section-title{{font-size:14px;font-weight:600;padding:12px 16px 4px;color:#58a6ff}}
.journal-table{{width:100%;border-collapse:collapse;font-size:12px;margin:0 16px;width:calc(100% - 32px)}}
.journal-table th{{background:#21262d;padding:8px;text-align:left;color:#8b949e;font-weight:500}}
.journal-table td{{padding:8px;border-bottom:1px solid #21262d}}
.health-bar{{display:flex;align-items:center;gap:8px;padding:10px 16px;background:#161b22;border-top:1px solid #30363d;font-size:13px}}
</style>
</head>
<body>

<div class="topbar">
  <div class="topbar-row1">
    <span class="logo">🎯 TIE TIY</span>
    <span class="nifty-price">
      Nifty: <span style="color:{n_color}">{nifty_px:,.0f} {n_arrow} {nifty_chg:+.1f}%</span>
    </span>
    <span class="regime-badge" style="background:{rc}">{regime} {reg_score:+d}</span>
  </div>
  <div class="topbar-row2">
    <span>📅 {today}</span>
    <span>🕐 Updated: {updated_at}</span>
    <span>{h_emoji} System: {health} ({health_wr}%)</span>
  </div>
</div>

{bear_banner}
{heatmap}

<div class="filter-bar">
  <button class="filter-btn active" onclick="filterSignals('all')">All ({len(signals)})</button>
  <button class="filter-btn" onclick="filterSignals('deploy')">✅ Deploy</button>
  <button class="filter-btn" onclick="filterSignals('watch')">👁 Watch</button>
  <button class="filter-btn" onclick="filterSignals('UP_TRI')">UP TRI</button>
  <button class="filter-btn" onclick="filterSignals('DOWN_TRI')">DOWN TRI</button>
  <button class="filter-btn" onclick="filterSignals('BULL_PROXY')">PROXY</button>
  <button class="filter-btn" onclick="filterSignals('age0')">Age 0</button>
  <button class="filter-btn" onclick="filterSignals('gradeA')">⭐ Grade A</button>
</div>

<div class="signals-container" id="signals">
{signal_cards}
</div>

<div class="section-title">📓 Journal — Open + Last 10</div>
<div style="overflow-x:auto;padding:0 0 12px">
<table class="journal-table">
  <tr>
    <th>Stock</th><th>Signal</th><th>Entry</th>
    <th>Stop</th><th>Exit Date</th><th>P&L</th><th>Status</th>
  </tr>
  {journal_rows}
</table>
</div>

<div class="health-bar">
  {h_emoji} System Health: <b>{health}</b> |
  WR last 5: {health_wr}% |
  Open positions: {len(open_trades)}
</div>

<script>
function filterSignals(f) {{
  document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));
  event.target.classList.add('active');
  document.querySelectorAll('.signal-card').forEach(c=>{{
    if(f==='all') c.style.display='';
    else if(f==='deploy') c.style.display=c.dataset.action==='DEPLOY'?'':'none';
    else if(f==='watch') c.style.display=c.dataset.action==='WATCH'?'':'none';
    else if(f==='UP_TRI') c.style.display=c.dataset.signal==='UP_TRI'?'':'none';
    else if(f==='DOWN_TRI') c.style.display=c.dataset.signal==='DOWN_TRI'?'':'none';
    else if(f==='BULL_PROXY') c.style.display=c.dataset.signal==='BULL_PROXY'?'':'none';
    else if(f==='age0') c.style.display=c.dataset.age==='0'?'':'none';
    else if(f==='gradeA') c.style.display=c.dataset.grade==='A'?'':'none';
  }});
}}
</script>
</body>
</html>'''

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(f"{OUTPUT_DIR}/index.html", 'w') as f:
        f.write(html)
    print(f"HTML saved to {OUTPUT_DIR}/index.html")
    return html
