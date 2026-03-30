import os
import sys
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))
from config import OUTPUT_DIR


def build_html(signals, market_info,
               sector_momentum, open_trades,
               recent_trades, system_health,
               rejected_signals=None):


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

    icons   = {'Leading': '🟢', 'Neutral': '🟡', 'Lagging': '🔴'}
    hm_html = '<div style="display:flex;flex-wrap:wrap;gap:6px;margin:8px 0;">'
    for sec, mom in sector_momentum.items():
        ic = icons.get(mom, '🟡')
        hm_html += (
            f'<span style="background:#0d1117;border:1px solid #30363d;'
            f'border-radius:12px;padding:3px 8px;font-size:10px;">'
            f'{ic} {sec}</span>')
    hm_html += '</div>'
        # Rejected signals section
    rejected_signals = rejected_signals or []
    rej_html = ''
    if rejected_signals:
        rej_rows = ''
        for s in rejected_signals:
            sym    = s.get('symbol','').replace('.NS','')
            signal = s.get('signal','')
            score  = s.get('score', 0)
            age    = s.get('age', 0)
            stop   = s.get('stop', 0)
            bd     = s.get('breakdown', '')
            arrow  = '▲' if signal in ('UP_TRI','BULL_PROXY') else '▼'
            # Build rejection reason
            reasons = []
            if score < 2:
                reasons.append(f'Score {score}/10 below minimum')
            if age > 1 and signal == 'DOWN_TRI':
                reasons.append('DOWN_TRI age>0 — edge gone')
            if not reasons:
                reasons.append(f'Score {score}/10')
            reason = ' | '.join(reasons)
            rej_rows += f'''<tr>
<td style="color:#666;">{sym}</td>
<td style="color:#666;">{signal} {arrow}</td>
<td style="color:#444;">{score}/10</td>
<td style="color:#444;">Age:{age}</td>
<td style="color:#555;font-size:10px;">{reason}</td>
</tr>'''
        rej_html = f'''
<div class="section-hdr" style="color:#444;border-color:#333;">
  <span onclick="toggleRej()" style="cursor:pointer;">
  ▶ REJECTED SIGNALS ({len(rejected_signals)})
  </span>
</div>
<div id="rej-section" style="display:none;overflow-x:auto;">
<table>
<tr>
  <th>Stock</th><th>Signal</th><th>Score</th>
  <th>Age</th><th>Reason</th>
</tr>
{rej_rows}
</table>
<div style="font-size:10px;color:#444;padding:6px 0;">
These signals were detected but did not meet minimum score threshold.
</div>
</div>'''
             

    all_journal = (list(open_trades or []) + list(recent_trades or []))
    jrows = ''
    for t in all_journal[:15]:
        stk    = t.get('stock', '').replace('.NS', '')
        stype  = t.get('signal_type', '')
        entry  = t.get('entry_actual', t.get('entry_estimate', ''))
        stp    = t.get('stop_price', '')
        exd    = t.get('exit_date_plan', '')
        pnl    = t.get('pnl_pct', '')
        status = t.get('status', '')
        sc2    = ('#00C851' if status == 'WON' else
                  '#f85149' if status in ('STOPPED', 'CLOSED') else '#FFD700')
        pnl_c  = '#f85149' if str(pnl).startswith('-') else '#00C851'
        jrows += f'''<tr>
<td style="color:#58a6ff;">{stk}</td>
<td>{stype}</td><td>₹{entry}</td>
<td style="color:#f85149;">₹{stp}</td>
<td>{exd}</td>
<td style="color:{pnl_c};">{pnl}%</td>
<td style="color:{sc2};">{status}</td>
</tr>'''

    html = f'''<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TIE TIY Scanner</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Arial,sans-serif;background:#07070f;
     color:#c9d1d9;padding:12px;max-width:600px;margin:0 auto;
     padding-bottom:80px;}}
.filter-btn{{background:#161b22;color:#8b949e;border:1px solid #30363d;
             border-radius:6px;padding:5px 10px;font-size:10px;
             cursor:pointer;margin:2px;}}
.filter-btn.active{{background:#58a6ff;color:#000;}}
table{{width:100%;border-collapse:collapse;font-size:11px;}}
th{{background:#161b22;color:#8b949e;padding:6px 8px;
    text-align:left;border-bottom:1px solid #21262d;}}
td{{padding:5px 8px;border-bottom:1px solid #0c0c1a;}}
.section-hdr{{color:#ffd700;font-size:11px;font-weight:700;
              border-left:3px solid #ffd700;padding-left:8px;
              margin:16px 0 8px;}}
#tap-overlay{{display:none;position:fixed;top:0;left:0;
              right:0;bottom:0;background:rgba(0,0,0,0.75);z-index:100;}}
#tap-panel{{position:fixed;bottom:0;left:50%;
            transform:translateX(-50%) translateY(100%);
            width:100%;max-width:600px;background:#0d1117;
            border-top:2px solid #30363d;border-radius:16px 16px 0 0;
            padding:16px 16px 32px;z-index:101;
            transition:transform 0.3s ease;}}
#tap-panel.open{{transform:translateX(-50%) translateY(0);}}
.panel-handle{{width:40px;height:4px;background:#30363d;
               border-radius:2px;margin:0 auto 14px;}}
.stat-box{{background:#161b22;border-radius:6px;padding:8px;}}
.stat-label{{color:#666;font-size:10px;margin-bottom:2px;}}
.stat-val{{font-size:14px;font-weight:700;}}
.pos-card{{background:#0d1117;border:1px solid #21262d;
           border-radius:8px;padding:10px 12px;margin-bottom:8px;}}
</style>
</head><body>

<div style="background:#0d1117;border:1px solid #21262d;
border-radius:10px;padding:12px 14px;margin-bottom:12px;">
  <div style="display:flex;justify-content:space-between;
  align-items:center;margin-bottom:4px;">
    <span style="color:#ffd700;font-size:18px;font-weight:700;">
    🎯 TIE TIY Scanner</span>
    <span style="color:{n_color};font-size:13px;">
    Nifty {nifty_px:,.0f} {n_arrow} {nifty_chg:+.1f}%</span>
  </div>
  <div style="display:flex;justify-content:space-between;
  font-size:11px;color:#8b949e;">
    <span>{today} | Updated {updated_at}</span>
    <span style="background:{rc};color:#000;border-radius:4px;
    padding:1px 7px;font-weight:700;">{regime} {reg_score:+d}</span>
  </div>
</div>

{bear_banner}
{hm_html}

<div style="display:flex;flex-wrap:wrap;gap:4px;margin:10px 0;">
<button class="filter-btn active" onclick="filterS('all',event)">All</button>
<button class="filter-btn" onclick="filterS('UP_TRI',event)">UP TRI</button>
<button class="filter-btn" onclick="filterS('DOWN_TRI',event)">DOWN TRI</button>
<button class="filter-btn" onclick="filterS('BULL_PROXY',event)">Proxy</button>
<button class="filter-btn" onclick="filterS('age0',event)">Age 0</button>
</div>

<div id="signals">
  <div style="color:#666;text-align:center;padding:20px;font-size:12px;">
  Loading signals...</div>
</div>

<div class="section-hdr">OPEN POSITIONS
  <span id="pos-count-badge"
  style="background:#161b22;color:#8b949e;border-radius:10px;
  padding:1px 7px;font-size:10px;margin-left:4px;">0</span>
</div>
<div id="positions-list">
  <div style="color:#444;font-size:11px;text-align:center;padding:14px;">
  No open positions — tap any signal card to add</div>
</div>

<div class="section-hdr">10-DAY SIGNAL LOG</div>
<div style="overflow-x:auto;">
<table id="journal-table">
<tr><th>Date</th><th>Stock</th><th>Signal</th>
    <th>Score</th><th>Entry</th><th>Stop</th><th>Age</th></tr>
<tr><td colspan="7" style="color:#666;text-align:center;
padding:12px;">Loading...</td></tr>
</table></div>

<div class="section-hdr">TRADE JOURNAL</div>
<div style="overflow-x:auto;"><table>
<tr><th>Stock</th><th>Signal</th><th>Entry</th>
    <th>Stop</th><th>Exit</th><th>PnL</th><th>Status</th></tr>
{jrows if jrows else
 '<tr><td colspan="7" style="color:#666;text-align:center;'
 'padding:12px;">No trades logged yet</td></tr>'}
</table></div>

<div style="margin-top:14px;padding:8px 12px;background:#0d1117;
border-radius:8px;font-size:11px;color:#8b949e;">
{h_emoji} System: {health} | WR last 5: {health_wr}% |
Open positions: <span id="pos-count-footer">0</span>
</div>

<div id="tap-overlay" onclick="closePanel()"></div>

<div id="tap-panel">
  <div class="panel-handle"></div>
  <div style="display:flex;justify-content:space-between;
  align-items:center;margin-bottom:14px;">
    <div>
      <span id="panel-symbol"
      style="font-size:22px;font-weight:700;color:#fff;"></span>
      <span id="panel-signal-badge"
      style="background:#161b22;color:#8b949e;border-radius:4px;
      padding:2px 7px;font-size:10px;margin-left:8px;"></span>
    </div>
    <button onclick="closePanel()"
    style="background:none;border:none;color:#666;
    font-size:22px;cursor:pointer;">✕</button>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;
  gap:8px;margin-bottom:10px;">
    <div class="stat-box">
      <div class="stat-label">LIVE PRICE</div>
      <div id="panel-live" class="stat-val" style="color:#58a6ff;">...</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">ENTRY EST</div>
      <div id="panel-entry" class="stat-val" style="color:#c9d1d9;">—</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">STOP LOSS</div>
      <div id="panel-stop" class="stat-val" style="color:#f85149;">—</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">TARGET</div>
      <div id="panel-target" class="stat-val" style="color:#00C851;">—</div>
    </div>
  </div>
  <div id="panel-pnl-row" style="display:none;
  background:#161b22;border-radius:6px;padding:8px 10px;
  margin-bottom:10px;font-size:12px;">
    <span style="color:#666;">Unrealized P&L: </span>
    <span id="panel-pnl-val" style="font-weight:700;font-size:14px;"></span>
    <span id="panel-pnl-pct" style="color:#666;font-size:11px;margin-left:6px;"></span>
  </div>
  <button id="panel-add-btn" onclick="addPosition()"
  style="width:100%;background:#238636;color:#fff;border:none;
  border-radius:6px;padding:11px;font-size:13px;font-weight:700;
  cursor:pointer;margin-bottom:6px;">+ Add to Positions</button>
  <button id="panel-remove-btn" onclick="removeCurrentPosition()"
  style="width:100%;background:#3a0a0a;color:#f85149;
  border:1px solid #f85149;border-radius:6px;padding:9px;
  font-size:12px;font-weight:700;cursor:pointer;
  display:none;margin-bottom:6px;">✕ Remove from Positions</button>
  <div id="panel-status"
  style="font-size:10px;color:#666;text-align:center;min-height:16px;"></div>
</div>

<script>
let currentCard = {{}};

async function loadSignals() {{
  const el = document.getElementById('signals');
  try {{
    const res  = await fetch('scan_log.json?t=' + Date.now());
    const data = await res.json();
    if (!Array.isArray(data) || !data.length) throw new Error('empty');
    const latest = data[data.length - 1];
    const sigs   = latest.signals || [];
    document.querySelector('.filter-btn').textContent =
      'All (' + sigs.length + ')';
    if (!sigs.length) {{
      el.innerHTML = '<div style="text-align:center;color:#666;'
        + 'padding:40px 20px;font-size:14px;">No signals on '
        + latest.date + '</div>';
      return;
    }}
    el.innerHTML = sigs.map(s => {{
      const sym    = (s.stock || s.symbol || '').replace('.NS','');
      const signal = s.signal || '';
      const score  = s.score  || 0;
      const entry  = s.entry  || 0;
      const stop   = s.stop   || 0;
      const target = s.target || 0;
      const age    = s.age    || 0;
      const sector = s.sector || '';
      const grade  = s.grade  || 'B';
      const sc     = score >= 7 ? '#00C851'
                   : score >= 4 ? '#FFD700' : '#f85149';
      const arrow  = signal.includes('DOWN') ? '▼' : '▲';
      const t_val  = target ? target.toFixed(2) : '0';
      return `<div class="signal-card"
        data-signal="${{signal}}" data-age="${{age}}"
        data-action="" data-grade="${{grade}}"
        data-symbol="${{sym}}"
        data-entry="${{entry.toFixed ? entry.toFixed(2) : entry}}"
        data-stop="${{stop.toFixed   ? stop.toFixed(2)  : stop}}"
        data-target="${{t_val}}" data-shares="0"
        data-sector="${{sector}}" data-score="${{score}}"
        onclick="openPanel(this)"
        style="background:#0d1117;border:1px solid #21262d;
        border-left:3px solid ${{sc}};border-radius:8px;
        padding:12px 14px;margin-bottom:10px;cursor:pointer;">
        <div style="display:flex;justify-content:space-between;
        margin-bottom:6px;">
          <div>
            <span style="font-size:16px;font-weight:700;color:#fff;">
            ${{sym || '?'}}</span>
            <span style="color:#666;font-size:11px;margin-left:6px;">
            ${{sector}}</span>
          </div>
          <span style="color:${{sc}};font-size:13px;font-weight:700;">
          ${{score}}/10</span>
        </div>
        <div style="color:#8b949e;font-size:11px;margin-bottom:6px;">
          ${{signal}} ${{arrow}} | Age:${{age}} | Grade:${{grade}}
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;
        gap:4px;font-size:12px;">
          <div>Entry: <span style="color:#58a6ff;">
          ${{entry ? '₹'+fmt(entry) : '—'}}</span></div>
          <div>Stop: <span style="color:#f85149;">
          ${{stop  ? '₹'+fmt(stop)  : '—'}}</span></div>
          ${{target
            ? '<div><span style="color:#58a6ff;">Target: ₹'
              +fmt(target)+'</span></div>'
            : '<div style="color:#666;">Exit: Day 6 open</div>'}}
        </div>
      </div>`;
    }}).join('');
  }} catch(e) {{
    el.innerHTML = '<div style="text-align:center;color:#666;'
      + 'padding:40px 20px;">Could not load signals</div>';
  }}
}}

function openPanel(el) {{
  const sym    = el.dataset.symbol;
  const entry  = parseFloat(el.dataset.entry)  || 0;
  const stop   = parseFloat(el.dataset.stop)   || 0;
  const target = parseFloat(el.dataset.target) || 0;
  const shares = parseInt(el.dataset.shares)   || 0;
  const signal = el.dataset.signal;
  const score  = el.dataset.score;
  currentCard  = {{ sym, entry, stop, target, shares, signal }};

  document.getElementById('panel-symbol').textContent =
    sym || '?';
  document.getElementById('panel-signal-badge').textContent =
    signal + ' | Score ' + score;
  document.getElementById('panel-entry').textContent =
    entry  ? '₹' + fmt(entry)  : '—';
  document.getElementById('panel-stop').textContent =
    stop   ? '₹' + fmt(stop)   : '—';
  document.getElementById('panel-target').textContent =
    target ? '₹' + fmt(target) : 'Day 6 open';
  document.getElementById('panel-live').textContent   = '...';
  document.getElementById('panel-pnl-row').style.display = 'none';
  document.getElementById('panel-status').textContent    = '';

  const inPos = getPositions().find(p => p.sym === sym);
  document.getElementById('panel-add-btn').style.display =
    inPos ? 'none' : 'block';
  document.getElementById('panel-remove-btn').style.display =
    inPos ? 'block' : 'none';

  document.getElementById('tap-overlay').style.display = 'block';
  document.getElementById('tap-panel').classList.add('open');

  if (sym) fetchLivePrice(sym);
}}

function closePanel() {{
  document.getElementById('tap-overlay').style.display = 'none';
  document.getElementById('tap-panel').classList.remove('open');
}}

async function fetchLivePrice(sym) {{
  const liveEl   = document.getElementById('panel-live');
  const statusEl = document.getElementById('panel-status');
  try {{
    const url = 'https://query2.finance.yahoo.com/v8/finance/chart/'
      + sym + '.NS?interval=1d&range=1d&t=' + Date.now();
    const res  = await fetch(url);
    const data = await res.json();
    const price =
      data?.chart?.result?.[0]?.meta?.regularMarketPrice;
    if (!price) throw new Error('no price');
    liveEl.textContent = '₹' + fmt(price);
    const pos = getPositions().find(p => p.sym === sym);
    if (pos && pos.entry) {{
      const diff   = price - pos.entry;
      const pct    = ((diff / pos.entry) * 100).toFixed(2);
      const pnlAmt = (diff * (pos.shares || 1)).toFixed(0);
      const color  = diff >= 0 ? '#00C851' : '#f85149';
      const sign   = diff >= 0 ? '+' : '';
      document.getElementById('panel-pnl-row').style.display =
        'block';
      document.getElementById('panel-pnl-val').style.color =
        color;
      document.getElementById('panel-pnl-val').textContent =
        sign + '₹' + pnlAmt;
      document.getElementById('panel-pnl-pct').textContent =
        '(' + sign + pct + '%)';
    }}
  }} catch(e) {{
    liveEl.textContent   = '—';
    statusEl.textContent = 'Live price unavailable';
  }}
}}

function getPositions() {{
  try {{
    return JSON.parse(
      localStorage.getItem('tietiy_pos') || '[]');
  }} catch(e) {{ return []; }}
}}

function savePositions(arr) {{
  localStorage.setItem('tietiy_pos', JSON.stringify(arr));
  renderPositions();
}}

function addPosition() {{
  const {{ sym, entry, stop, shares, signal }} = currentCard;
  if (!sym) return;
  const arr = getPositions();
  if (arr.find(p => p.sym === sym)) {{
    document.getElementById('panel-status').textContent =
      'Already in positions';
    return;
  }}
  arr.push({{ sym, entry, stop, shares, signal,
    added: new Date().toISOString().slice(0,10) }});
  savePositions(arr);
  document.getElementById('panel-add-btn').style.display =
    'none';
  document.getElementById('panel-remove-btn').style.display =
    'block';
  document.getElementById('panel-status').textContent =
    '✓ Added';
}}

function removeCurrentPosition() {{
  removePosition(currentCard.sym);
  document.getElementById('panel-add-btn').style.display =
    'block';
  document.getElementById('panel-remove-btn').style.display =
    'none';
  document.getElementById('panel-pnl-row').style.display =
    'none';
  document.getElementById('panel-status').textContent =
    'Removed';
}}

function removePosition(sym) {{
  savePositions(getPositions().filter(p => p.sym !== sym));
}}

function renderPositions() {{
  const arr = getPositions();
  const cnt = arr.length;
  document.getElementById('pos-count-badge').textContent  = cnt;
  document.getElementById('pos-count-footer').textContent = cnt;
  const el = document.getElementById('positions-list');
  if (!cnt) {{
    el.innerHTML =
      '<div style="color:#444;font-size:11px;'
      + 'text-align:center;padding:14px;">'
      + 'No open positions — tap any signal card to add</div>';
    return;
  }}
  el.innerHTML = arr.map(p => `
    <div class="pos-card">
      <div style="display:flex;justify-content:space-between;
      align-items:center;">
        <div>
          <span style="font-weight:700;color:#fff;
          font-size:15px;">${{p.sym}}</span>
          <span style="color:#666;font-size:10px;
          margin-left:8px;">${{p.signal}} | ${{p.added}}</span>
        </div>
        <button onclick="removePosition('${{p.sym}}')"
          style="background:none;border:1px solid #f85149;
          color:#f85149;border-radius:4px;padding:3px 8px;
          font-size:10px;cursor:pointer;">Exit</button>
      </div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);
      gap:4px;margin-top:8px;font-size:11px;">
        <div style="color:#666;">Entry<br>
          <span style="color:#58a6ff;">
          ${{p.entry ? '₹'+fmt(p.entry) : '—'}}</span></div>
        <div style="color:#666;">Stop<br>
          <span style="color:#f85149;">
          ${{p.stop  ? '₹'+fmt(p.stop)  : '—'}}</span></div>
        <div style="color:#666;">Shares<br>
          <span style="color:#c9d1d9;">
          ${{p.shares || '—'}}</span></div>
      </div>
    </div>`).join('');
}}

async function loadJournal() {{
  const tbl = document.getElementById('journal-table');
  const header = `<tr><th>Date</th><th>Stock</th>
    <th>Signal</th><th>Score</th><th>Entry</th>
    <th>Stop</th><th>Age</th></tr>`;
  try {{
    const res  = await fetch('scan_log.json?t=' + Date.now());
    const data = await res.json();
    if (!Array.isArray(data) || !data.length)
      throw new Error('empty');
    const rows = [];
    data.slice(-10).reverse().forEach(day => {{
      (day.signals || []).forEach(s => {{
        rows.push({{
          date:   day.date || '',
          stock:  (s.stock || s.symbol || '').replace('.NS',''),
          signal: s.signal || '',
          score:  s.score  || 0,
          entry:  s.entry  || 0,
          stop:   s.stop   || 0,
          age:    s.age    || 0
        }});
      }});
    }});
    if (!rows.length) throw new Error('no rows');
    const tbody = rows.slice(0,40).map(r => {{
      const sc  = r.score >= 7 ? '#00C851'
                : r.score >= 4 ? '#FFD700' : '#f85149';
      const arr = r.signal.includes('DOWN') ? '▼' : '▲';
      return `<tr>
        <td style="color:#555;white-space:nowrap;">
          ${{r.date}}</td>
        <td style="color:#58a6ff;">${{r.stock || '?'}}</td>
        <td>${{r.signal}} ${{arr}}</td>
        <td style="color:${{sc}};">${{r.score}}</td>
        <td>${{r.entry ? '₹'+fmt(r.entry) : '—'}}</td>
        <td style="color:#f85149;">
          ${{r.stop ? '₹'+fmt(r.stop) : '—'}}</td>
        <td style="color:#666;">${{r.age}}</td>
      </tr>`;
    }}).join('');
    tbl.innerHTML = header + tbody;
  }} catch(e) {{
    tbl.innerHTML = header +
      '<tr><td colspan="7" style="color:#666;'
      + 'text-align:center;padding:12px;">'
      + 'Could not load signal log</td></tr>';
  }}
}}

function filterS(f, ev) {{
  document.querySelectorAll('.filter-btn')
    .forEach(b => b.classList.remove('active'));
  ev.target.classList.add('active');
  document.querySelectorAll('.signal-card').forEach(c => {{
    const show = (
      f === 'all' ||
      (f === 'UP_TRI'     && c.dataset.signal === 'UP_TRI') ||
      (f === 'DOWN_TRI'   && c.dataset.signal === 'DOWN_TRI') ||
      (f === 'BULL_PROXY' && c.dataset.signal === 'BULL_PROXY') ||
      (f === 'age0'       && c.dataset.age === '0')
    );
    c.style.display = show ? '' : 'none';
  }});
}}

function fmt(n) {{
  return parseFloat(n).toLocaleString('en-IN',
    {{minimumFractionDigits:2,maximumFractionDigits:2}});
}}

renderPositions();
loadSignals();
loadJournal();
</script>
</body></html>'''

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = f"{OUTPUT_DIR}/index.html"
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(html)
    print(f"HTML saved to {path}")
    return html
