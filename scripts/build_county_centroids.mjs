// County centroids projected with the same Albers USA settings as data/states.js (scale 1300, translate 487.5,305).
// Run once: npm i us-atlas@3.0.1 topojson-client@3.1.0 d3-geo@3.1.0 && node scripts/build_county_centroids.mjs
// Writes data/shift/counties.json: { fips: [name, state, cx, cy] } plus "02000" for Alaska as a whole (its results are reported statewide).
import fs from 'fs';
import { createRequire } from 'module';
import * as topojson from 'topojson-client';
import { geoPath, geoAlbersUsa } from 'd3-geo';
const require = createRequire(import.meta.url);
const us = require('us-atlas/counties-10m.json');
const path = geoPath(geoAlbersUsa().scale(1300).translate([487.5, 305]));
const ST = {"01":"AL","02":"AK","04":"AZ","05":"AR","06":"CA","08":"CO","09":"CT","10":"DE","11":"DC","12":"FL","13":"GA","15":"HI","16":"ID","17":"IL","18":"IN","19":"IA","20":"KS","21":"KY","22":"LA","23":"ME","24":"MD","25":"MA","26":"MI","27":"MN","28":"MS","29":"MO","30":"MT","31":"NE","32":"NV","33":"NH","34":"NJ","35":"NM","36":"NY","37":"NC","38":"ND","39":"OH","40":"OK","41":"OR","42":"PA","44":"RI","45":"SC","46":"SD","47":"TN","48":"TX","49":"UT","50":"VT","51":"VA","53":"WA","54":"WV","55":"WI","56":"WY"};
const out = {};
for (const f of topojson.feature(us, us.objects.counties).features) {
  const st = ST[f.id.slice(0, 2)]; if (!st) continue;
  const c = path.centroid(f); if (!isFinite(c[0])) continue;
  out[f.id] = [f.properties.name, st, +c[0].toFixed(1), +c[1].toFixed(1)];
}
// Alaska as one unit
const ak = topojson.feature(us, us.objects.states).features.find(f => f.id === '02');
if (ak) { const c = path.centroid(ak); out['02000'] = ['Alaska', 'AK', +c[0].toFixed(1), +c[1].toFixed(1)]; }
fs.mkdirSync('data/shift', { recursive: true });
fs.writeFileSync('data/shift/counties.json', JSON.stringify(out));
console.log(Object.keys(out).length, 'counties');
