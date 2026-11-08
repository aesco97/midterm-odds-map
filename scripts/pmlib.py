"""Shared helpers for the data scripts: HTTP with a curl fallback, and a cached Polymarket Gamma lookup."""
import json, pathlib, subprocess, tempfile, time, urllib.request, urllib.error

UA = 'presidentl.app data scripts (github.com/aesco97/midterm-odds-map)'
CACHE = pathlib.Path(tempfile.gettempdir()) / 'presidentl-gamma'

def get(url, timeout=60, retries=3):
    """GET url as text. Falls back to curl when Python has no root certificates (python.org builds on macOS)."""
    last = None
    for i in range(retries):
        try:
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=timeout) as r:
                    return r.read().decode('utf-8', 'replace')
            except urllib.error.URLError as e:
                if 'CERTIFICATE_VERIFY_FAILED' not in str(e): raise
                out = subprocess.run(['curl', '-sSL', '--fail', '--max-time', str(timeout), '-A', UA, url], check=True, capture_output=True)
                return out.stdout.decode('utf-8', 'replace')
        except Exception as e:  # 429s and blips: back off and retry
            last = e; time.sleep(1.5 * (i + 1))
    raise last

def get_json(url, **kw):
    return json.loads(get(url, **kw))

def gamma_event(slug, cache=True):
    """The Gamma event for a Polymarket event slug (markets, prices, token ids), or None. Cached on disk for reruns."""
    CACHE.mkdir(exist_ok=True)
    f = CACHE / (slug + '.json')
    if cache and f.exists():
        return json.loads(f.read_text(encoding='utf-8'))
    data = get_json('https://gamma-api.polymarket.com/events?slug=' + slug)
    ev = data[0] if isinstance(data, list) and data else None
    if ev is not None: f.write_text(json.dumps(ev), encoding='utf-8')
    return ev

def market_outcomes(ev):
    """[{name, party, yes_price, yes_token, closed, won}] for each candidate market of an event; placeholder outcomes dropped."""
    out = []
    for m in ev.get('markets', []):
        name = (m.get('groupItemTitle') or m.get('question') or '').strip()
        if not name or len(name) <= 2 or name.startswith(('Person ', 'Option ', 'Candidate ', 'Party ')): continue
        try: prices = [float(x) for x in json.loads(m.get('outcomePrices') or '[]')]
        except (ValueError, TypeError): prices = []
        try: tokens = json.loads(m.get('clobTokenIds') or '[]')
        except (ValueError, TypeError): tokens = []
        party = ''
        if name.endswith('(D)'): party = 'D'
        elif name.endswith('(R)'): party = 'R'
        elif name.endswith(')'): party = 'I'
        elif name.lower().startswith('democrat'): party = 'D'   # party-level markets: "Democratic Party", "Democrat"
        elif name.lower().startswith('republican'): party = 'R'
        clean = name.rsplit(' (', 1)[0] if name.endswith(')') else name
        out.append({'name': clean, 'party': party, 'yes_price': prices[0] if prices else None, 'yes_token': tokens[0] if tokens else None,
                    'closed': bool(m.get('closed')), 'won': bool(prices) and prices[0] >= 0.999 and bool(m.get('closed')), 'volume': m.get('volume')})
    return out
