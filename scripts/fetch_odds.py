"""Refresh data/odds.json from PolymarketTrader.com's free feed of Polymarket prices (CC BY 4.0), then run build.py.

Usage: python3 scripts/fetch_odds.py            # download the feed
       python3 scripts/fetch_odds.py feed.json  # use an already-downloaded copy
"""
import json, pathlib, urllib.request, subprocess, sys
root = pathlib.Path(__file__).resolve().parent.parent
URL = 'https://polymarkettrader.com/api/v1/midterms-2026.json'
STATE_CODE = {"Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR","California":"CA","Colorado":"CO","Connecticut":"CT","Delaware":"DE","Florida":"FL","Georgia":"GA","Hawaii":"HI","Idaho":"ID","Illinois":"IL","Indiana":"IN","Iowa":"IA","Kansas":"KS","Kentucky":"KY","Louisiana":"LA","Maine":"ME","Maryland":"MD","Massachusetts":"MA","Michigan":"MI","Minnesota":"MN","Mississippi":"MS","Missouri":"MO","Montana":"MT","Nebraska":"NE","Nevada":"NV","New Hampshire":"NH","New Jersey":"NJ","New Mexico":"NM","New York":"NY","North Carolina":"NC","North Dakota":"ND","Ohio":"OH","Oklahoma":"OK","Oregon":"OR","Pennsylvania":"PA","Rhode Island":"RI","South Carolina":"SC","South Dakota":"SD","Tennessee":"TN","Texas":"TX","Utah":"UT","Vermont":"VT","Virginia":"VA","Washington":"WA","West Virginia":"WV","Wisconsin":"WI","Wyoming":"WY"}
# Markets that list candidates without party labels: name -> party
PARTY_FIX = {"alaska-senate-election-winner": {"Mary Peltola": "D", "Sen. Dan Sullivan": "R"},
             "alaska-governor-election-winner": {"Jonathan Kreiss-Tomkins": "D", "Bernadette Wilson": "R"},
             "california-governor-election-2026": {"Xavier Becerra": "D", "Steve Hilton": "R"}}

def control(ch):
    out = {"D": 0, "R": 0}
    for o in ch.get("control", []):
        if o["outcome"].startswith("Dem"): out["D"] = o["price"]
        if o["outcome"].startswith("Rep"): out["R"] = o["price"]
    return out

def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "midterm-odds-map/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.URLError as e:  # python.org builds often lack root certs; curl has its own
        if "CERTIFICATE_VERIFY_FAILED" not in str(e): raise
        out = subprocess.run(["curl", "-sSL", "-A", "midterm-odds-map/1.0", url], check=True, capture_output=True)
        return json.loads(out.stdout)

def fetch(): return get_json(URL)

def main():
    src = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")) if len(sys.argv) > 1 else fetch()
    sen = src["chambers"]["senate"]; hou = src["chambers"]["house"]; gov = src["chambers"]["governor"]
    def state_races(ch):  # Senate and governor races share a shape: one market per state, candidates with parties
        out = []
        for r in ch["races"]:
            cands = []
            for c in r["candidates"]:
                party = c.get("party") or PARTY_FIX.get(r["market"], {}).get(c["name"], "")
                if c["price"] >= 0.005: cands.append({"name": c["name"], "party": party, "price": c["price"]})
            rec = {"state": STATE_CODE[r["race"]], "name": r["race"], "market": r["market"], "rating": r.get("rating"), "volume": round(r.get("volume", 0)), "cands": cands}
            k = r.get("kalshi")
            if k and k.get("ticker"): rec["kalshi"] = {"ticker": k["ticker"], "D": k.get("D"), "R": k.get("R")}
            out.append(rec)
        return out
    senate_races = state_races(sen); governor_races = state_races(gov)
    house_races = []
    for r in hou["races"]:
        rec = {"id": r["race"], "market": r["market"], "rating": r.get("rating"), "volume": round(r.get("volume", 0))}
        others = []
        for c in r["candidates"]:
            if len(c["name"]) == 1: continue  # placeholder outcomes (A, B, C...)
            if c["party"] in ("D", "R") and c["party"] not in rec: rec[c["party"]] = {"name": c["name"], "price": c["price"]}
            elif c["party"] not in ("D", "R") and c["price"] >= 0.01: others.append(c)
        rec.setdefault("D", {"name": "Democrat", "price": 0}); rec.setdefault("R", {"name": "Republican", "price": 0})
        if others:
            o = max(others, key=lambda c: c["price"]); rec["other"] = {"name": o["name"], "price": o["price"]}
        house_races.append(rec)
    house_races.sort(key=lambda r: r["id"])
    data = {"updated": src["updated"],
            "senate": {"control": control(sen), "seats": sen.get("seats", []), "races": senate_races},
            "house": {"control": control(hou), "seats": hou.get("seats", []), "races": house_races},
            "governor": {"seats": gov.get("seats", []), "races": governor_races}}
    (root/'data/odds.json').write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"odds.json: {len(senate_races)} Senate · {len(house_races)} House · {len(governor_races)} Governor · updated {src['updated']}")
    snapshot(data)
    fetch_2028()
    subprocess.run([sys.executable, str(root/'scripts/build.py')], check=True)

MARKETS_2028 = [  # PolymarketTrader single-market feed slugs (= Polymarket event slugs)
    ("presidential-election-winner-2028", "2028 presidential election winner"),
    ("democratic-presidential-nominee-2028", "Democratic nominee"),
    ("republican-presidential-nominee-2028", "Republican nominee"),
]
PARTY_2028 = {  # party hints for the winner market; nominee markets are single-party
    "JD Vance": "R", "J.D. Vance": "R", "Marco Rubio": "R", "Donald Trump Jr.": "R", "Ron DeSantis": "R", "Vivek Ramaswamy": "R", "Ted Cruz": "R", "Glenn Youngkin": "R", "Nikki Haley": "R", "Tucker Carlson": "R", "Greg Abbott": "R", "Josh Hawley": "R", "Rand Paul": "R", "Tim Scott": "R",
    "Gavin Newsom": "D", "Alexandria Ocasio-Cortez": "D", "Josh Shapiro": "D", "Pete Buttigieg": "D", "Andy Beshear": "D", "Gretchen Whitmer": "D", "Kamala Harris": "D", "Wes Moore": "D", "JB Pritzker": "D", "Cory Booker": "D", "Zohran Mamdani": "D", "Rahm Emanuel": "D", "Ruben Gallego": "D", "Tim Walz": "D", "Chris Murphy": "D", "Jon Ossoff": "D", "Mark Cuban": "D", "Jared Polis": "D", "Amy Klobuchar": "D", "Stephen A. Smith": "D", "Jasmine Crockett": "D", "Raphael Warnock": "D",
}

def _pick(d, *keys, default=None):
    for k in keys:
        if isinstance(d, dict) and d.get(k) is not None: return d[k]
    return default

def _num(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v / 100 if v > 1 else v  # accept 0.2 or 20 (%)

def _ts(v):
    """Unix seconds from an ISO date/datetime or epoch (s or ms)."""
    from datetime import datetime, timezone
    if isinstance(v, (int, float)): return int(v / 1000 if v > 1e11 else v)
    try:
        dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except ValueError:
        return None

def fetch_2028():
    """Pull the three 2028 presidential markets into data/odds_2028.json.

    The single-market feed (/api/v1/odds/<slug>.json) is parsed defensively: outcomes may be listed under
    'outcomes' or 'markets' with name/outcome/label and probability/price/prob fields, and the 30-day history
    under 'history' as [{date, price}] or {outcome: [...]} shapes. Anything unparseable is skipped, never fatal."""
    out = {"updated": None, "markets": []}
    for slug, title in MARKETS_2028:
        try:
            src = get_json(f"https://polymarkettrader.com/api/v1/odds/{slug}.json")
        except Exception as e:  # keep the last good file rather than fail the build
            print(f"2028: could not fetch {slug}: {e}"); continue
        out["updated"] = _pick(src, "updated", "updated_at", "asOf", default=out["updated"])
        raw = _pick(src, "outcomes", "markets", "candidates", "options", default=[])
        if isinstance(raw, dict): raw = [dict(name=k, **(v if isinstance(v, dict) else {"price": v})) for k, v in raw.items()]
        outcomes, hist = [], {}
        for o in raw:
            if not isinstance(o, dict): continue
            name = _pick(o, "name", "outcome", "label", "title", "candidate")
            price = _num(_pick(o, "probability", "price", "prob", "p", "yes"))
            if not name or price is None: continue
            rec = {"name": str(name).strip(), "price": round(price, 4)}
            ch = _num(_pick(o, "change24h", "change_24h", "delta24h", "change"))
            if ch is not None: rec["change24h"] = round(ch, 4)
            vol = _pick(o, "volume", "vol")
            if isinstance(vol, (int, float)): rec["volume"] = round(vol)
            party = PARTY_2028.get(rec["name"]) or ("D" if "democratic" in slug else "R" if "republican" in slug else "")
            if party: rec["party"] = party
            outcomes.append(rec)
            h = _pick(o, "history", "prices", "series")
            if isinstance(h, list):
                pts = []
                for e in h:
                    if isinstance(e, dict): t, pr = _ts(_pick(e, "date", "t", "time", "timestamp")), _num(_pick(e, "price", "p", "probability", "value"))
                    elif isinstance(e, (list, tuple)) and len(e) >= 2: t, pr = _ts(e[0]), _num(e[1])
                    else: continue
                    if t is not None and pr is not None: pts.append([t, round(pr, 4)])
                if len(pts) >= 2: hist[rec["name"]] = pts
        # market-level history keyed by outcome name
        mh = _pick(src, "history", "series")
        if isinstance(mh, dict):
            for name, h in mh.items():
                if not isinstance(h, list) or name in hist: continue
                pts = []
                for e in h:
                    if isinstance(e, dict): t, pr = _ts(_pick(e, "date", "t", "time", "timestamp")), _num(_pick(e, "price", "p", "probability", "value"))
                    elif isinstance(e, (list, tuple)) and len(e) >= 2: t, pr = _ts(e[0]), _num(e[1])
                    else: continue
                    if t is not None and pr is not None: pts.append([t, round(pr, 4)])
                if len(pts) >= 2: hist[name] = pts
        outcomes.sort(key=lambda o: -o["price"])
        out["markets"].append({"slug": slug, "title": _pick(src, "title", "question", default=title), "label": title,
                               "volume": _pick(src, "volume", "total_volume"), "outcomes": outcomes[:25], "history": hist})
        print(f"2028: {slug}: {len(outcomes)} outcomes, history for {len(hist)}")
    if out["markets"]:
        (root/'data/odds_2028.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')

def snapshot(data):
    """Append one compact price snapshot per feed update to data/history/ (Democratic price per race).

    build.py folds these into the page's history series (deltas, sparklines, movers). A file is written
    only when the feed's `updated` stamp is new, so the hourly workflow adds about two files a day."""
    hist = root/'data/history'; hist.mkdir(exist_ok=True)
    stamp = data['updated'][:16].replace(':', '-')  # 2026-10-22T13-50
    out = hist/f'{stamp}.json'
    if out.exists(): return
    def dprice(cands):  # Democratic price; in races with no priced Democrat (NE, ID...), the non-Republican share
        d = next((c for c in cands if c['party'] == 'D'), None)
        r = next((c for c in cands if c['party'] == 'R'), None)
        if d: return round(d['price'], 3)
        return round(1 - r['price'], 3) if r else None
    snap = {'updated': data['updated'],
            'control': {'senate': data['senate']['control']['D'], 'house': data['house']['control']['D']},
            'senate': {r['state']: dprice(r['cands']) for r in data['senate']['races']},
            'governor': {r['state']: dprice(r['cands']) for r in data['governor']['races']},
            'house': {r['id']: round(r['D']['price'], 3) for r in data['house']['races']}}
    out.write_text(json.dumps(snap, separators=(',', ':')), encoding='utf-8')
    print(f"history: wrote {out.name}")

if __name__ == "__main__":
    main()
