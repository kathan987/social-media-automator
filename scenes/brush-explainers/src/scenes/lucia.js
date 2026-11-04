// lucia.js v2: "The real reason Lucia went to prison" (GTA 6). Facts: Rockstar's profile via GTA Wiki + rockstargames.com/VI.
// L1 (3.4 s) her father taught her to fight: his worn glove and her small one hang side by side in warm blind-light.
// L2 (4.6 s) fighting for her family landed her in the Leonida Penitentiary: a watchtower at dusk, the fence draws closed.
// L3 (6 s)   sheer luck got her out: a chain-link gate swings open onto a Leonida sunrise.

function glove(key, cx, cy, s, rot, col, lace = '#EDE3D2') {
  wc(key + 'cast', ellPts(cx + 60 * s, cy + 40 * s, 120 * s, 160 * s, 26, 6 * s), '#2A1A12', 70, { bleed: .4, tex: .3, border: 0 });  // soft shadow on the wall
  push(); translate(cx, cy); rotate(rot);
  stillSeed(key + 'str'); inkLine([[0, -420 * s], [-30 * s, -190 * s]], .6, '#3A2A22', 'pen');  // the lace it hangs from
  inkLine([[0, -420 * s], [32 * s, -190 * s]], .6, '#3A2A22', 'pen');
  wc(key + 'cuff', rrPts(-80 * s, 95 * s, 160 * s, 110 * s, 22 * s), mixCol(col, '#1A0F0C', .35), 200, { wash: mixCol(col, '#1A0F0C', .3), washOp: 255, tex: .75, ink: '#1A0F0C', sw: .4, br: 'HB' });
  wc(key + 'body', ellPts(10 * s, -20 * s, 112 * s, 150 * s, 30, 5 * s), col, 210, { wash: col, washOp: 255, tex: .75, border: .6, ink: '#2A1A16', sw: .45, br: 'HB' });
  wc(key + 'thumb', ellPts(-92 * s, 8 * s, 42 * s, 80 * s, 20, 3 * s, .35), mixCol(col, '#1A0F0C', .25), 210, { wash: mixCol(col, '#1A0F0C', .2), washOp: 255, tex: .6 });
  shade(key + 'sh', ellPts(55 * s, 10 * s, 70 * s, 130 * s, 22), '#2A1210', 9 * s + 4, 70, 'charcoal', .9, .6);
  wc(key + 'dark', ellPts(60 * s, 30 * s, 60 * s, 120 * s, 22, 4 * s), '#1A0B08', 90, { bleed: .3, tex: .6, border: .2 });
  stillSeed(key + 'lace'); for (let i = 0; i < 4; i++) inkLine([[-36 * s, (118 + i * 22) * s], [36 * s, (130 + i * 22) * s]], .6, lace, 'pen');
  stillSeed(key + 'stitch'); inkLine([[-70 * s, -60 * s], [-20 * s, -150 * s], [60 * s, -150 * s], [110 * s, -40 * s]], .5, mixCol(col, '#F1E4CC', .5), 'pen', .6);
  glow(-30 * s, -95 * s, 70 * s, '#FFD9A0', .45);
  pop();
}

function L1(t, lt, dur) {
  camBegin(W / 2, 760, 1.02 + .05 * ease(seg(lt, 0, dur)));
  bands('L1wall', ['#A98260', '#8C6A4E', '#6A4C38', '#3E2C20'], -300, 2100);
  for (let i = 0; i < 5; i++) {  // light through blinds, drifting slowly across the wall
    const x = -200 + i * 150 + lt * 18;
    wc('blind' + i, [[x, 120], [x + 70, 120], [x + 420, 1300], [x + 350, 1300]], '#F6D7A8', 40, { bleed: .3, tex: .3, border: .05 });
  }
  shade('L1grain', rectPts(-40, 1250, W + 80, 700), '#4A3226', 22, -20, 'charcoal', .6, .7);  // floorboards in charcoal
  stillSeed('nail'); paint(ellPts(540, 330, 9, 9, 12), { wash: '#2A2420', ink: null });
  glove('big', 420, 800, 1.6, .05 * Math.sin(t * 1.4), '#7A2620');
  glove('small', 640, 960, .95, .07 * Math.sin(t * 1.9 + 1.3), '#C8423A');
  camEnd();
  glow(220, 260, 520, '#FFC98A', .5);
  if (lt > dur - .35) flash(seg(lt, dur - .35, dur) * .9, '#2A2533');
}

function L2(t, lt, dur) {
  if (lt < .35) flash(1 - seg(lt, 0, .35), '#2A2533');
  camBegin(W / 2, 900, 1.06 - .05 * ease(seg(lt, 0, dur)));
  bands('L2sky', ['#3E3A66', '#6B547E', '#B9707A', '#E59A74', '#F2C08A'], -80, 1000);
  glow(760, 930, 360, '#FFB67A', .9);
  wc('L2sun', ellPts(760, 930, 70, 70, 30), '#FCE2B0', 220, { wash: '#FBE0AE', washOp: 255, bleed: .1 });
  wc('L2block', [[-40, 860], [1120, 830], [1120, 1000], [-40, 1000]], '#2A2740', 230, { wash: '#262338', washOp: 255, tex: .6 });
  for (let i = 0; i < 9; i++) { const lit = hash(i * 7) > .45; stillSeed('win' + i); paint(rectPts(80 + i * 110, 900, 22, 16), { wash: lit ? '#F4C27A' : '#1B1828', ink: null }); if (lit) glow(91 + i * 110, 908, 26, '#FFC66B', .7); }
  // watchtower: charcoal legs, painted cabin, a lamp that comes on
  for (const [a, b] of [[[220, 1000], [250, 560]], [[330, 1000], [300, 560]], [[230, 820], [320, 700]], [[320, 820], [230, 700]]]) sketch('leg' + a[0] + b[1], [a, b], 1.6, '#1B1828', 'charcoal', 0);
  wc('cab', rectPts(205, 470, 140, 100), '#2B2638', 240, { wash: '#29243A', washOp: 255 });
  wc('roof', [[185, 475], [365, 475], [275, 410]], '#1F1B2C', 240, { wash: '#1F1B2C', washOp: 255 });
  const lamp = ease(seg(lt, .6, 1.2));
  glow(275, 520, 160, '#FFE2A0', lamp);
  const sw = Math.sin(t * .9) * .35;  // searchlight sweeping across the yard
  wc('beam', [[275, 520], [275 + Math.cos(.9 + sw) * 1100 - 160, 520 + Math.sin(.9 + sw) * 1100], [275 + Math.cos(.9 + sw) * 1100 + 160, 520 + Math.sin(.9 + sw) * 1100 - 120]], '#FFF1C8', 45 * lamp, { bleed: .35, tex: .2, border: 0 });
  bands('L2yard', ['#3B3346', '#2C2636'], 1000, 1980, 200);
  // the fence closes across the frame as the voice says "landed her in"
  const k = easeOut(seg(lt, 1.1, 2.6)), fx = lerp(W + 60, -60, k);
  for (let x = W + 60; x >= fx; x -= 230) sketch('post' + x, [[x, 640], [x + 4, 1460]], 2.2, '#15121C', 'charcoal', 0);
  if (k > .02) {
    chainLink('mesh', [[fx, 680], [W + 60, 680], [W + 60, 1440], [fx, 1440]], '#120F18', 26, .95);
    razorWire('rw', fx, W + 60, 650, 34, 1, '#15121C');
  }
  camEnd();
  if (lt > dur - .35) flash(seg(lt, dur - .35, dur), '#F6E2C0');
}

function L3(t, lt, dur) {
  if (lt < .35) flash(1 - seg(lt, 0, .35), '#F6E2C0');
  const open = ease(seg(lt, .7, 3.6)), ang = open * 1.25;
  camBegin(W / 2, 860, 1.0 + .07 * ease(seg(lt, 0, dur)));
  bands('L3sky', ['#9FC3D6', '#C9D3C8', '#F4D2A4', '#F3B07C'], -80, 1060);
  glow(540, 1000, 300 + 420 * open, '#FFD58A', .55 + .45 * open);
  wc('L3sun', ellPts(540, 1010, 95, 95, 30), '#FFF0C6', 230, { wash: '#FFEFC4', washOp: 255, bleed: .08 });
  wc('sea', rectPts(-60, 1030, W + 120, 90), '#5E8C8A', 200, { wash: '#6E9A94', washOp: 255, tex: .4 });
  palm('p1', 90, 1060, 520, '#2E3A3A', 230); palm('p2', 960, 1060, 430, '#2E3A3A', 230); palm('p3', 1010, 1060, 300, '#3A4747', 200);
  wc('ground', rectPts(-60, 1110, W + 120, 900), '#B88F67', 190, { wash: '#A98563', washOp: 255, tex: .8 });
  wc('path', [[470, 1110], [610, 1110], [900, 1980], [180, 1980]], '#E9CFA4', 140, { bleed: .2, tex: .6 });
  wc('light', [[300, 1110], [780, 1110], [1000, 1980], [80, 1980]], '#FFE6B0', 60 * open, { bleed: .3, tex: .2, border: 0 });
  // fence panels either side, then the two gate leaves swinging toward us
  chainLink('fl', [[-60, 470], [240, 470], [240, 1230], [-60, 1230]], '#1A1D22', 24, .8);
  chainLink('fr', [[840, 470], [W + 60, 470], [W + 60, 1230], [840, 1230]], '#1A1D22', 24, .8);
  razorWire('rwl', -60, 240, 440, 30, 1, '#1E2228'); razorWire('rwr', 840, W + 60, 440, 30, 1, '#1E2228');
  const leaf = (key, hx, dir) => {
    const w = 300 * Math.cos(ang), grow = 140 * Math.sin(ang), ox = hx + dir * w;
    const P = [[hx, 470], [ox, 470 - grow], [ox, 1230 + grow], [hx, 1230]];
    if (w > 6) chainLink(key, P, '#1A1D22', 24, .85);
    sketch(key + 'f', P.concat([P[0]]), 1.3, '#16191E', 'pen', 0);
  };
  leaf('gl', 240, 1); leaf('gr', 840, -1);
  sketch('post1', [[240, 430], [240, 1240]], 2, '#121418', 'charcoal', 0); sketch('post2', [[840, 430], [840, 1240]], 2, '#121418', 'charcoal', 0);
  if (open > .5) for (let i = 0; i < 26; i++) {  // dust in the light
    const x = 300 + hash(i) * 480 + Math.sin(t * .7 + i) * 20, y = 700 + hash(i + 40) * 500 - (t * 14 + i * 9) % 160;
    glow(x, y, 6 + hash(i + 5) * 8, '#FFF3D0', (open - .5) * 1.4);
  }
  camEnd();
}

shots([[0, L1], [3.4, L2], [8, L3]]);
