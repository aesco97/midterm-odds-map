// Regenerate data/districts.js from the Census cartographic boundary file for the 119th Congress.
// Needs node + `npm i mapshaper d3-geo` (only for this script; the page itself has no dependencies).
//
//   curl -LO https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_cd119_500k.zip && unzip cb_2024_us_cd119_500k.zip
//   node scripts/build_districts.js cb_2024_us_cd119_500k.shp
//
// Shapes are simplified (topology-preserving) and projected with the same Albers USA settings
// us-atlas uses for data/states.js (scale 1300, translate 487.5,305) so districts sit exactly on the states.
const path = require('path'), fs = require('fs');
const mapshaper = require('mapshaper'), { geoAlbersUsa } = require('d3-geo');
const FIPS = {"01":"AL","02":"AK","04":"AZ","05":"AR","06":"CA","08":"CO","09":"CT","10":"DE","12":"FL","13":"GA","15":"HI","16":"ID","17":"IL","18":"IN","19":"IA","20":"KS","21":"KY","22":"LA","23":"ME","24":"MD","25":"MA","26":"MI","27":"MN","28":"MS","29":"MO","30":"MT","31":"NE","32":"NV","33":"NH","34":"NJ","35":"NM","36":"NY","37":"NC","38":"ND","39":"OH","40":"OK","41":"OR","42":"PA","44":"RI","45":"SC","46":"SD","47":"TN","48":"TX","49":"UT","50":"VT","51":"VA","53":"WA","54":"WV","55":"WI","56":"WY"};
const shp = process.argv[2]; if (!shp) { console.error('usage: node scripts/build_districts.js <cb_2024_us_cd119_500k.shp>'); process.exit(1); }
(async () => {
  const out = await mapshaper.applyCommands(`-i "${shp}" -simplify 5% keep-shapes -clean -o out.json format=geojson precision=0.0001`, {});
  const gj = JSON.parse(out['out.json']);
  const proj = geoAlbersUsa().scale(1300).translate([487.5, 305]);
  // Project vertex by vertex (not via geoPath) so ring winding never matters and the far Aleutians,
  // which fall outside the Alaska inset, simply drop out.
  const districts = {};
  for (const f of gj.features) {
    const st = FIPS[f.properties.STATEFP]; if (!st) continue; // territories / DC have no House race
    const cd = f.properties.CD119FP; if (cd === 'ZZ') continue; // undefined areas (water)
    if (cd === '00') continue; // at-large districts: the page reuses the state outline from data/states.js
    const id = st + '-' + cd;
    const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
    let d = '', sx = 0, sy = 0, n = 0, area = 0, cxs = 0, cys = 0;
    for (const poly of polys) for (const ring of poly) {
      const pts = []; for (const ll of ring) { const q = proj(ll); if (!q) continue; const x = +q[0].toFixed(1), y = +q[1].toFixed(1); const l = pts[pts.length - 1]; if (l && l[0] === x && l[1] === y) continue; pts.push([x, y]); }
      if (pts.length < 4) continue;
      let a = 0, cx = 0, cy = 0; // ring centroid (shoelace); the label goes in the biggest piece
      for (let i = 0; i < pts.length; i++) { const [x0, y0] = pts[i], [x1, y1] = pts[(i + 1) % pts.length]; const w = x0 * y1 - x1 * y0; a += w; cx += (x0 + x1) * w; cy += (y0 + y1) * w; }
      if (Math.abs(a) / 2 < 0.2 && pts.length < 12) continue; // specks under 0.2 px² (islets) are invisible even zoomed in
      d += 'M' + pts.map(p => p[0] + ',' + p[1]).join('L') + 'Z';
      if (Math.abs(a) > Math.abs(area)) { area = a; cxs = cx / (3 * a); cys = cy / (3 * a); }
    }
    if (!d) continue;
    districts[id] = { d, cx: +cxs.toFixed(1), cy: +cys.toFixed(1) };
  }
  const ids = Object.keys(districts).sort();
  const js = 'const DISTRICTS=' + JSON.stringify(Object.fromEntries(ids.map(k => [k, districts[k]]))) + ';\n';
  fs.writeFileSync(path.join(__dirname, '..', 'data', 'districts.js'), js);
  console.log(`data/districts.js: ${ids.length} districts, ${(js.length / 1024) | 0} KB`);
})();
