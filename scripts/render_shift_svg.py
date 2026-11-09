"""Reference renderer for the shift maps (NYT-style arrows), from data/shift/*.json.

  python3 scripts/render_shift_svg.py president 2024 2020 out.svg     # 2024 result, arrows = change in margin since 2020
  python3 scripts/render_shift_svg.py house 2018 2014 out.svg

Arrow: starts at the county centroid, points up-left (bluer) or up-right (redder); length = |margin shift| in points
(capped), width grows with county turnout. Counties flagged 1 (one-party / unopposed House races) in either year are skipped.
The site's live version lives in src/shift.html; keep the two in step.
"""
import json, math, re, sys, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
office, y1, y0, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
C = json.loads((root/'data/shift/counties.json').read_text()); R = json.loads((root/'data/shift/results.json').read_text())
states = json.loads(re.search(r'const STATES=(\{.*?\});\nconst MESH', (root/'data/states.js').read_text(), re.S).group(1))
margin = lambda v: (v[0]-v[1])/v[2]*100 if v[2] else None
a, b = R[office][y1], R[office][y0]
SCALE, CAP, HS, ANG = 2.6, 55, 2.2, math.radians(40)
svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 975 610" style="background:#fff">']
for s in states.values(): svg.append(f'<path d="{s["d"]}" fill="#f2f2f2" stroke="#fff" stroke-width="1"/>')
n = 0
for f, v in a.items():
    if f not in b or f not in C or v[3] or b[f][3]: continue
    m1, m0 = margin(v), margin(b[f])
    if m1 is None or m0 is None: continue
    d = m1 - m0; x, y = C[f][2], C[f][3]; L = min(CAP, abs(d)*SCALE)
    if L < 1.5: continue
    dx, dy = L*math.cos(ANG), -L*math.sin(ANG)
    if d > 0: dx = -dx
    col = '#2f6fd0' if d > 0 else '#d6453f'; w = 0.7 + min(1.3, v[2]/200000)
    x2, y2 = x+dx, y+dy; ux, uy = dx/L, dy/L; px, py = -uy, ux
    svg.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" stroke-width="{w:.1f}" stroke-opacity=".8"/>')
    svg.append(f'<polygon points="{x2:.1f},{y2:.1f} {x2-ux*HS*2.2+px*HS:.1f},{y2-uy*HS*2.2+py*HS:.1f} {x2-ux*HS*2.2-px*HS:.1f},{y2-uy*HS*2.2-py*HS:.1f}" fill="{col}" fill-opacity=".9"/>')
    n += 1
svg.append('</svg>')
pathlib.Path(out).write_text('\n'.join(svg)); print(f'{out}: {n} arrows')
