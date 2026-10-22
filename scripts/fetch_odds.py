"""Refresh data/odds.json from PolymarketTrader.com's free feed of Polymarket prices (CC BY 4.0), then run build.py.

Usage: python3 scripts/fetch_odds.py            # download the feed
       python3 scripts/fetch_odds.py feed.json  # use an already-downloaded copy
"""
import json, pathlib, urllib.request, subprocess, sys
root = pathlib.Path(__file__).resolve().parent.parent
URL = 'https://polymarkettrader.com/api/v1/midterms-2026.json'
STATE_CODE = {"Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR","California":"CA","Colorado":"CO","Connecticut":"CT","Delaware":"DE","Florida":"FL","Georgia":"GA","Hawaii":"HI","Idaho":"ID","Illinois":"IL","Indiana":"IN","Iowa":"IA","Kansas":"KS","Kentucky":"KY","Louisiana":"LA","Maine":"ME","Maryland":"MD","Massachusetts":"MA","Michigan":"MI","Minnesota":"MN","Mississippi":"MS","Missouri":"MO","Montana":"MT","Nebraska":"NE","Nevada":"NV","New Hampshire":"NH","New Jersey":"NJ","New Mexico":"NM","New York":"NY","North Carolina":"NC","North Dakota":"ND","Ohio":"OH","Oklahoma":"OK","Oregon":"OR","Pennsylvania":"PA","Rhode Island":"RI","South Carolina":"SC","South Dakota":"SD","Tennessee":"TN","Texas":"TX","Utah":"UT","Vermont":"VT","Virginia":"VA","Washington":"WA","West Virginia":"WV","Wisconsin":"WI","Wyoming":"WY"}
# Markets that list candidates without party labels: name -> party
PARTY_FIX = {"alaska-senate-election-winner": {"Mary Peltola": "D", "Sen. Dan Sullivan": "R"}}

def control(ch):
    out = {"D": 0, "R": 0}
    for o in ch.get("control", []):
        if o["outcome"].startswith("Dem"): out["D"] = o["price"]
        if o["outcome"].startswith("Rep"): out["R"] = o["price"]
    return out

def fetch():
    req = urllib.request.Request(URL, headers={"User-Agent": "midterm-odds-map/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.URLError as e:  # python.org builds often lack root certs; curl has its own
        if "CERTIFICATE_VERIFY_FAILED" not in str(e): raise
        out = subprocess.run(["curl", "-sSL", "-A", "midterm-odds-map/1.0", URL], check=True, capture_output=True)
        return json.loads(out.stdout)

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
            out.append({"state": STATE_CODE[r["race"]], "name": r["race"], "market": r["market"], "rating": r.get("rating"), "volume": round(r.get("volume", 0)), "cands": cands})
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
    subprocess.run([sys.executable, str(root/'scripts/build.py')], check=True)

if __name__ == "__main__":
    main()
