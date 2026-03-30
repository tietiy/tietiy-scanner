import os
import sys
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))
from config import OUTPUT_DIR


def build_html(signals, market_info,
               sector_momentum, open_trades,
               recent_trades, system_health):

    today      = market_info.get('today', '')
    regime     = market_info.get('regime', 'Choppy')
    reg_score  = market_info.get('regime_score', 0)
    nifty_px   = market_info.get('nifty_price', 0)
    nifty_chg  = market_info.get('nifty_change', 0)
    health     = system_health.get('health', 'NORMAL')
    health_wr  = system_health.get('health_wr', 0)
    updated_at = datetime.now().strftime('%H:%M')

    rc      = ('#FF4444' if regime == 'Bear' else
               '#00C851' if regime == 'Bull' else
               '#FFD700')
    n_color = '#00C851' if nifty_chg >= 0 else '#FF4444'
    n_arrow = '▲' if nifty_chg >= 0 else '▼'
    h_emoji = ('🟢' if health == 'HOT' else
               '🔴' if health == 'COLD' else '🟡')

    bear_banner = ''
    if regime == 'Bear':
        bear_banner = '''
<div style="background:#1a0a0a;border:1px solid #ff4444;
border-radius:8px;padding:10px 14px;margin:8px 0;
color:#ff6666;font-size:12px;font-weight:700;">
BEAR BONUS ACTIVE — UP TRI signals highest conviction
</div>'''

    # Sector heatmap
    icons   = {'Leading':'🟢','Neutral':'🟡','Lagging':'🔴'}
    hm_html = '<div style="display:flex;flex-wrap:wrap;gap:6px;margin:8px 0;">'
    for sec, mom in sector_momentum.items():
        ic = icons.get(mom, '🟡')
        hm_html += (
            f'<span style="background:#0d1117;border:1px solid #30363d;'
            f'border-radius:12px;padding:3px 8px;font-size:10px;">'
            f'{ic} {sec}</span>')
    hm_html += '</div>'

    # Signal cards
    signal_cards = ''
    if not signals:
        signal_cards = '''
<div style="text-align:center;color:#666;
padding:40px 20px;font-size:14px;">
No signals today
</div>'''
    else:
        for sig in signals:
            action   = sig.get('action', '')
            score    = sig.get('score', 0)
            signal   = sig.get('signal', '')
            symbol   = sig.get('symbol','').replace(
                '.NS','')
            sector   = sig.get('sector', '')
            age      = sig.get('age', 0)
            regime_s = sig.get('regime', '')
            vol_q    = sig.get('vol_q', '')
            rs_q     = sig.get('rs_q', '')
            entry    = sig.get('entry_est', 0)
            stop     = sig.get('stop', 0)
            target   = sig.get('target', None)
            rr       = sig.get('rr', None)
            shares   = sig.get('shares', 0)
            risk     = sig.get('risk_amt', 0)
            ex_date  = sig.get('exit_date', '')
            bear_b   = sig.get('bear_bonus', False)
            grade    = sig.get('grade', 'B')
            bdown    = sig.get('breakdown', '')

            ac = ('#00C851' if action == 'DEPLOY' else
                  '#FFD700' if action == 'WATCH' else
                  '#FF8800')
            sc = ('#00C851' if score >= 7 else
                  '#FFD700' if score >= 4 else '#FF4444')
            arrow = '▲' if signal in (
                'UP_TRI','BULL_PROXY') else '▼'
            bb_badge = (
                '<span style="background:#3a1a00;'
                'color:#ff8800;border-radius:4px;'
                'padding:1px 5px;font-size:9px;'
                'font-weight:700;margin-left:4px;">'
                'BEAR BONUS</span>'
                if bear_b else '')

            tgt_line = (
                f'<span style="color:#58a6ff;">'
                f'Target: ₹{target:,.2f} | R:R {rr}x'
                f'</span>'
                if target else
                f'<span style="color:#666;">'
                f'Exit: {ex_date} open</span>')

            signal_cards += f'''
<div class="signal-card"
     data-action="{action}"
     data-signal="{signal}"
     data-age="{age}"
     data-grade="{grade}"
     style="background:#0d1117;border:1px solid #21262d;
     border-left:3px solid {ac};border-radius:8px;
     padding:12px 14px;margin-bottom:10px;">
  <div style="display:flex;justify-content:space-between;
  align-items:flex-start;margin-bottom:6px;">
    <div>
      <span style="font-size:16px;font-weight:700;
      color:#fff;">{symbol}</span>
      {bb_badge}
      <span style="color:#666;font-size:11px;
      margin-left:6px;">{sector}</span>
    </div>
    <div style="text-align:right;">
      <span style="background:{ac};color:#000;
      border-radius:4px;padding:2px 7px;
      font-size:10px;font-weight:700;">{action}</span>
      <span style="display:block;color:{sc};
      font-size:11px;margin-top:2px;">{score}/10</span>
    </div>
  </div>
  <div style="color:#8b949e;font-size:11px;
  margin-bottom:6px;">
    {signal} {arrow} | Age:{age} | {regime_s} |
    Vol:{vol_q} | RS:{rs_q}
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;
  gap:4px;font-size:12px;margin-bottom:6px;">
    <div>Entry: <span style="color:#58a6ff;">
    ₹{entry:,.2f}</span></div>
    <div>Stop: <span style="color:#f85149;">
    ₹{stop:,.2f}</span></div>
    <div>{tgt_line}</div>
    <div style="color:#666;">
    {shares} sh | Risk ₹{risk:,.0f}</div>
  </div>
  <div style="color:#444;font-size:9px;">{bdown}</div>
</div>'''

    # Journal rows
    all_journal = (list(open_trades or []) +
                   list(recent_trades or []))
    jrows = ''
    for t in all_journal[:15]:
        stk    = t.get('stock','').replace('.NS','')
        stype  = t.get('signal_type','')
        entry  = t.get('entry_actual',
                        t.get('entry_estimate',''))
        stp    = t.get('stop_price','')
        exd    = t.get('exit_date_plan','')
        pnl    = t.get('pnl_pct','')
        status = t.get('status','')
        sc     = ('#00C851' if status == 'WON' else
                  '#f85149' if status in (
                      'STOPPED','CLOSED') else
                  '#FFD700')
        pnl_c  = ('#00C851' if str(pnl).startswith(
                      '-') is False and pnl else
                  '#f85149')
        jrows += f'''<tr>
<td style="color:#58a6ff;">{stk}</td>
<td>{stype}</td>
<td>₹{entry}</td>
<td style="color:#f85149;">₹{stp}</td>
<td>{exd}</td>
<td style="color:{pnl_c};">{pnl}%</td>
<td style="color:{sc};">{status}</td>
</tr>'''

    html = f'''<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport"
      content="width=device-width,initial-scale=1">
<title>TIE TIY Scanner</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Arial,sans-serif;
     background:#07070f;color:#c9d1d9;
     padding:12px;max-width:600px;margin:0 auto}}
.filter-btn{{background:#161b22;color:#8b949e;
             border:1px solid #30363d;border-radius:6px;
             padding:5px 10px;font-size:10px;
             cursor:pointer;margin:2px}}
.filter-btn.active{{background:#58a6ff;color:#000}}
table{{width:100%;border-collapse:collapse;
       font-size:11px}}
th{{background:#161b22;color:#8b949e;
    padding:6px 8px;text-align:left;
    border-bottom:1px solid #21262d}}
td{{padding:5px 8px;border-bottom:1px solid #0c0c1a}}
</style>
</head><body>
<div style="background:#0d1117;border:1px solid #21262d;
border-radius:10px;padding:12px 14px;margin-bottom:12px;">
  <div style="display:flex;justify-content:space-between;
  align-items:center;margin-bottom:4px;">
    <span style="color:#ffd700;font-size:18px;
    font-weight:700;">TIE TIY</span>
    <span style="color:{n_color};font-size:13px;">
    Nifty {nifty_px:,.0f} {n_arrow}
    {nifty_chg:+.1f}%</span>
  </div>
  <div style="display:flex;justify-content:space-between;
  font-size:11px;color:#8b949e;">
    <span>{today} | Updated {updated_at}</span>
    <span style="background:{rc};color:#000;
    border-radius:4px;padding:1px 7px;font-weight:700;">
    {regime} {reg_score:+d}</span>
  </div>
</div>
{bear_banner}
{hm_html}
<div style="display:flex;flex-wrap:wrap;
gap:4px;margin:10px 0;">
<button class="filter-btn active"
        onclick="filterS('all')">
All ({len(signals)})</button>
<button class="filter-btn"
        onclick="filterS('deploy')">Deploy</button>
<button class="filter-btn"
        onclick="filterS('watch')">Watch</button>
<button class="filter-btn"
        onclick="filterS('UP_TRI')">UP TRI</button>
<button class="filter-btn"
        onclick="filterS('DOWN_TRI')">DOWN TRI</button>
<button class="filter-btn"
        onclick="filterS('BULL_PROXY')">Proxy</button>
<button class="filter-btn"
        onclick="filterS('age0')">Age 0</button>
</div>
<div id="signals">{signal_cards}</div>
<div style="color:#ffd700;font-size:11px;
font-weight:700;border-left:3px solid #ffd700;
padding-left:8px;margin:14px 0 8px;">
JOURNAL</div>
<div style="overflow-x:auto;">
<table>
<tr><th>Stock</th><th>Signal</th><th>Entry</th>
<th>Stop</th><th>Exit</th><th>PnL</th>
<th>Status</th></tr>
{jrows if jrows else
 '<tr><td colspan="7" style="color:#666;'
 'text-align:center;padding:12px;">No trades</td>'
 '</tr>'}
</table></div>
<div style="margin-top:12px;padding:8px 12px;
background:#0d1117;border-radius:8px;
font-size:11px;color:#8b949e;">
{h_emoji} System: {health} | WR last 5: {health_wr}% |
Open: {len(open_trades)}
</div>
<script>
function filterS(f){{
  document.querySelectorAll('.filter-btn').forEach(
    b=>b.classList.remove('active'));
  event.target.classList.add('active');
  document.querySelectorAll('.signal-card').forEach(
    c=>{{
      if(f==='all') c.style.display='';
      else if(f==='deploy')
        c.style.display=
          c.dataset.action==='DEPLOY'?'':'none';
      else if(f==='watch')
        c.style.display=
          c.dataset.action==='WATCH'?'':'none';
      else if(f==='UP_TRI'||f==='DOWN_TRI'
              ||f==='BULL_PROXY')
        c.style.display=
          c.dataset.signal===f?'':'none';
      else if(f==='age0')
        c.style.display=
          c.dataset.age==='0'?'':'none';
    }});
}}
</script>
</body></html>'''

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = f"{OUTPUT_DIR}/index.html"
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(html)
    print(f"HTML saved to {path}")
    return html
