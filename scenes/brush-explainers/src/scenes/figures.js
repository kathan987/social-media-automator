// figures.js: the painting kit for the explainer beats (Vice Lowdown v2, owner 2026-11-03: "subtle aesthetic and painted
// brush", not childish). No cartoon people: still lifes, landscapes, silhouettes, light. Brushes by job:
//   watercolour fill (bleed/tex/border)  skies, walls, gloves, blood blooms     charcoal / dry   shadows, smears, posts
//   HB / 2H / cpencil                    sketch lines, anatomy, rim light        pen / rotring    chain-link, wire, ink writing
//   spray                                mist (the cough), dust                  hatch            pencil shading, mesh
// Static shapes use stillSeed(key) (no boil), so a painting holds still and only what moves changes.

const stillSeed = key => { let h = 2166136261; for (const c of String(key)) h = Math.imul(h ^ c.charCodeAt(0), 16777619); randomSeed(h >>> 0); };

// watercolour shape: o = { bleed, tex, border, wash (flat underlayer colour), washOp, ink, sw, br }
function wc(key, pts, col, op = 140, o = {}) {
  stillSeed(key);
  paint(pts, { fill: col, fillOp: op, bleed: o.bleed ?? .18, tex: o.tex ?? .5, border: o.border ?? .35, wash: o.wash, washOp: o.washOp, ink: o.ink ?? null, sw: o.sw, br: o.br });
}
// layered horizontal washes, top to bottom (skies, walls)
function bands(key, cols, y0, y1, op = 170) {
  // a smooth gradient of thin flat strips, then a few large loose watercolour passes for texture
  const N = 36, h = (y1 - y0) / N;
  for (let i = 0; i < N; i++) {
    const u = i / (N - 1) * (cols.length - 1), j = Math.min(cols.length - 2, Math.floor(u));
    stillSeed(key + 's' + i); paint(rectPts(-80, y0 + i * h - 2, W + 160, h + 4), { wash: mixCol(cols[j], cols[j + 1], u - j), washOp: 255, ink: null });
  }
  for (let i = 0; i < cols.length; i++)
    wc(key + 't' + i, ellPts(W * (.2 + .6 * hash(i * 13 + 1)), lerp(y0, y1, (i + .5) / cols.length), 760, (y1 - y0) / cols.length * .7, 30), cols[i], op * .35, { bleed: .35, tex: .7, border: .2 });
}
function sketch(key, pts, sw = 1, col = PAL.ink, br = 'HB', curv = .5) { stillSeed(key); inkLine(pts, sw, col, br, curv); }
function drawOn(pts, k, sw = 1, col = PAL.ink, br = 'ink') {
  const C = through(pts, 8), n = Math.floor(C.length * clamp(k));
  if (n >= 2) inkLine(C.slice(0, n), sw, col, br, 0);
}
// pencil / charcoal shading inside a shape
function shade(key, pts, col, d = 14, a = 50, br = 'charcoal', w = .8, grad = .4) {
  stillSeed(key); paint(pts, { hatch: { d, a, o: { rand: .35, gradient: grad }, b: br, c: col, w }, ink: null });
}
// chain-link mesh inside a polygon: two hatch directions with a fine technical pen
function chainLink(key, pts, col = '#1E1B26', d = 26, w = .55) {
  stillSeed(key + 'a'); paint(pts, { hatch: { d, a: 45, o: { rand: .04 }, b: 'rotring', c: col, w }, ink: null });
  stillSeed(key + 'b'); paint(pts, { hatch: { d, a: -45, o: { rand: .04 }, b: 'rotring', c: col, w }, ink: null });
}
// razor wire: a row of pen loops along y, drawn on to k (0..1)
function razorWire(key, x0, x1, y, r, k, col = '#1E1B26') {
  const pts = []; for (let x = x0; x <= x1; x += r * .55) { const a = (x - x0) / (r * .55) * 2.1; pts.push([x + Math.cos(a) * r * .5, y + Math.sin(a) * r]); }
  stillSeed(key); drawOn(pts, k, .7, col, 'pen');
}
// a palm silhouette: curved trunk + drooping frond ribbons
function palm(key, x, y, h, col = '#2E3A3A', op = 255) {
  const top = [x + h * .12, y - h];
  stillSeed(key); paint(ribbon([[x, y], [x + h * .05, y - h * .5], top], h * .05, h * .025), { wash: col, washOp: op, ink: null });
  for (let i = 0; i < 7; i++) {
    const a = -Math.PI / 2 + (i - 3) * .55, L = h * (.28 + .06 * hash(i + x));
    const p1 = [top[0] + Math.cos(a) * L * .55, top[1] + Math.sin(a) * L * .55 - L * .1], p2 = [top[0] + Math.cos(a) * L, top[1] + Math.sin(a) * L + L * .35];
    stillSeed(key + 'f' + i); paint(ribbon([top, p1, p2], h * .045, h * .005), { wash: col, washOp: op, ink: null });
  }
}
// Arthur in profile (facing right), feet of the shape at the bottom; unit box 0..1 scaled by s from (x, y) = top-left
const PROFILE = [[.08, 1], [.06, .74], [.16, .62], [.3, .57], [.36, .5], [.33, .44], [.36, .4], [.42, .37], [.47, .33], [.46, .3],
  [.5, .27], [.49, .245], [.45, .22], [.46, .2], [.44, .175], [.44, .15], [.6, .14], [.62, .12], [.45, .115], [.44, .06],
  [.4, .02], [.24, 0], [.12, .03], [.1, .1], [.02, .12], [.0, .14], [.12, .155], [.12, .22], [.1, .3], [.12, .38], [.02, .5], [0, .62], [0, 1]];
const placeP = (P, x, y, s) => P.map(([u, v]) => [x + u * s, y + v * s]);
