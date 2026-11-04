// arthur.js v2: "What really killed Arthur Morgan" (RDR2). Facts: Red Dead Wiki (Thomas Downes, Money Lending and Other
// Sins III), Wikipedia, and a playthrough of the mission (Downes coughs blood onto Arthur's face at 1:17).
// A1 (5 s)   Strauss's debt: a ledger by candlelight, "Thomas Downes" underlined in red ink.
// A2 (6 s)   the rake, the beating, the cough: Arthur's profile against a ranch at dusk; a red mist blooms across it.
// A3 (8.5 s) the diagnosis and the journal: anatomical pencil lungs with spreading spots, then his own words.
const JOURNAL = '"Caveat"';

function A1(t, lt, dur) {
  camBegin(W / 2, 760, 1.03 + .06 * ease(seg(lt, 0, dur)), -.02 + .015 * ease(seg(lt, 0, dur)));
  bands('desk', ['#3A2418', '#4A3022', '#3A2418'], -100, 2000);
  for (let i = 0; i < 9; i++) sketch('grain' + i, [[-60, 140 + i * 210], [500, 170 + i * 210 + 30 * hash(i)], [W + 60, 150 + i * 210]], 1.2, '#2A190F', 'dry', .6);
  wc('page', rrPts(120, 220, 840, 1080, 14), '#EADBB8', 200, { wash: '#E6D5B0', washOp: 255, tex: .7, border: .55 });
  shade('pageedge', [[120, 1150], [960, 1150], [960, 1300], [120, 1300]], '#8A6A46', 10, 0, 'HB', .5, .7);
  wc('stain', ellPts(780, 420, 120, 105, 30), '#B98E5C', 70, { bleed: .25, tex: .6, border: .8 });
  for (let i = 0; i < 12; i++) sketch('rule' + i, [[170, 400 + i * 66], [910, 403 + i * 66]], .5, '#B7A27E', '2H', 0);
  letter('Loans', 540, 310, 92, '#3A2A20', { font: `92px ${JOURNAL}`, ink: false, alpha: .9 });
  [0, 1, 3, 4, 6, 7, 9].forEach((r, i) => {  // other debtors: unreadable pen scribble (no invented names)
    const y = 445 + r * 66, pts = []; for (let j = 0; j <= 16; j++) pts.push([180 + j * 30, y + Math.sin(j * 2.1 + r) * 9 - 6]);
    stillSeed('scr' + r); drawOn(pts, seg(lt, .05 + i * .07, .45 + i * .07), .6, '#2B2220', 'pen');
    letter('$', 860, y - 8, 46, '#5A4A3A', { font: `46px ${JOURNAL}`, ink: false, alpha: .7 * seg(lt, .3 + i * .07, .6 + i * .07) });
  });
  const dy = 445 + 2 * 66 - 8;
  letter('Thomas Downes', 190, dy, 76, '#231A16', { font: `76px ${JOURNAL}`, align: 'left', ink: false, alpha: seg(lt, .6, 1.0) });
  stillSeed('red'); drawOn([[180, dy + 34], [420, dy + 38], [640, dy + 33]], seg(lt, 1.5, 2.1), 1.8, '#8E1B1B', 'rotring');
  stillSeed('red2'); drawOn([[200, dy + 48], [600, dy + 46]], seg(lt, 2.0, 2.4), 1.2, '#8E1B1B', 'rotring');
  for (let i = 0; i < 3; i++) wc('coin' + i, ellPts(250 + i * 70, 1220 + (i % 2) * 20, 46, 40, 24), '#C9A24A', 220, { wash: '#B8913E', washOp: 255, ink: '#5A4320', sw: .5, br: 'HB' });
  // a candle: flame flickers, its light breathes over the page
  wc('candle', rrPts(880, 900, 90, 330, 12), '#EFE6D0', 220, { wash: '#E8DEC6', washOp: 255 });
  const fl = 1 + .12 * Math.sin(t * 17) + .08 * Math.sin(t * 29);
  stillSeed('flame'); paint(ellPts(925, 862, 16, 34 * fl, 16), { wash: '#F6B84B', ink: null });
  camEnd();
  glow(925, 860, 300 * fl, '#FFB45A', .9);
  if (lt > dur - .35) flash(seg(lt, dur - .35, dur), '#1A120E');
}

function A2(t, lt, dur) {
  if (lt < .35) flash(1 - seg(lt, 0, .35), '#1A120E');
  const C = 3.6;
  const sh = lt > C && lt < C + .45 ? shakeXY(t, 12) : (lt > 2 && lt < 3.3 && Math.sin(lt * 9) > .6) ? shakeXY(t, 7) : [0, 0];
  const zoom = 1 + .05 * ease(seg(lt, 0, C)) + .12 * ease(seg(lt, C, dur));
  camBegin(W / 2 + sh[0] - 120 * ease(seg(lt, C, dur)), 900 + sh[1], zoom);
  bands('A2sky', ['#3B2A2A', '#6E4434', '#B9724A', '#E2A66E', '#EBC08A'], -100, 1080);
  glow(760, 1010, 340, '#FFB060', .8);
  wc('house', [[650, 1060], [650, 940], [760, 870], [870, 940], [870, 1060]], '#2A1E1A', 240, { wash: '#2A1E1A', washOp: 255 });
  stillSeed('win'); paint(rectPts(735, 965, 34, 28), { wash: '#F2B85E', ink: null }); glow(752, 979, 40, '#FFC66B', .8);
  for (let i = 0; i < 8; i++) sketch('fp' + i, [[30 + i * 140, 1080], [33 + i * 140, 1020]], 1.6, '#24180F', 'charcoal', 0);
  sketch('rail', [[0, 1040], [W, 1046]], 1.2, '#24180F', 'charcoal', 0);
  bands('A2ground', ['#4A3426', '#3A281D'], 1070, 2000, 210);
  // Downes: a fainter silhouette on the right, held up by the collar
  const pull = ease(seg(lt, 2.0, 2.4));
  const D = placeP(PROFILE.map(([u, v]) => [1 - u, v]), 400 - 40 * pull, 610 + 30 * pull, 760);
  wc('downes', D, '#3A2C26', 200, { wash: '#3E302A', washOp: 235, tex: .5 });
  // Arthur: a dark profile with a warm rim of light along his face
  const A = placeP(PROFILE, -60, 420, 900);
  wc('arthur', A, '#1E1714', 240, { wash: '#1A1310', washOp: 255, tex: .6 });
  shade('arthurT', A, '#2E231D', 12, 35, 'charcoal', .6, .5);
  stillSeed('rim'); inkLine(placeP(PROFILE.slice(3, 17), -60, 420, 900), 1.1, '#E8A060', 'cpencil', .5);
  // the rake swing: a dark smear across the frame
  const rk = seg(lt, .45, .85);
  if (rk > 0 && rk < 1) for (let j = 0; j < 4; j++) { stillSeed('rake' + j); inkLine([[1000 + j * 16, 300 - j * 12], [lerp(1000, 300, rk) + j * 16, lerp(300, 1100, rk) - j * 12]], 3.2 * (1 - rk) + .6, '#120C0A', 'dry', .2); }
  // the beating: three charcoal slashes, each fading fast
  [2.15, 2.55, 2.95].forEach((b, i) => { const a = lt - b; if (a > 0 && a < .3) { stillSeed('hit' + i); inkLine([[520 + i * 30, 640 + i * 40], [700 - i * 20, 760 + i * 30]], 4 * (1 - a / .3), '#120C0A', 'charcoal', .3); } });
  if (lt > C) {  // the cough: red mist sprays from Downes to Arthur's face, then blooms into the paper
    const mouth = [D[8][0], D[8][1]], face = [A[9][0] + 10, A[9][1]], q = easeOut(seg(lt, C, C + .4));
    stillSeed('mist'); brush.noFill(); brush.noHatch(); brush.noWash();
    for (let i = 0; i < 4; i++) { brush.set('spray', '#8E1B1B', 2.2 - i * .4); brush.line(mouth[0], mouth[1] + i * 10, lerp(mouth[0], face[0], q), lerp(mouth[1], face[1], q) + (i - 1.5) * 26); }
    [[0, 0, 70], [-40, 40, 46], [30, -30, 38], [-10, 90, 30], [60, 50, 26]].forEach(([dx, dy, r], i) => {
      const g = ease(seg(lt, C + .2 + i * .1, C + 1.4 + i * .1)); if (g > 0) wc('bloom' + i, ellPts(face[0] + dx, face[1] + dy, r * g, r * .85 * g, 22), '#8E1B1B', 150, { bleed: .3, tex: .7, border: .7 });
    });
  }
  camEnd();
  if (lt > C) flash(.28 * Math.exp(-(lt - C) * 6), '#9B2A22');
  if (lt > dur - .35) flash(seg(lt, dur - .35, dur), '#E9DDC3');
}

const LUNG_L = [[505, 470], [440, 448], [360, 500], [305, 610], [282, 760], [300, 880], [360, 930], [440, 920], [495, 860], [512, 700], [505, 470]];
const LUNG_R = LUNG_L.map(([x, y]) => [W - x, y]);
const QUOTE = ['"All them bullets shot at me,', 'all them horses threw me,', 'all them fights, and it was', 'the beating of that pathetic', 'little fella Downes', 'that killed me, I reckon."'];

function A3(t, lt, dur) {
  if (lt < .35) flash(1 - seg(lt, 0, .35), '#E9DDC3');
  camBegin(W / 2, 760, 1.02 + .04 * ease(seg(lt, 0, dur)));
  bands('jp', ['#E9DDC3', '#E3D4B6'], -100, 2000, 200);
  wc('jpage', rrPts(60, 150, W - 120, 1150, 10), '#F2E8D2', 200, { wash: '#F0E5CC', washOp: 255, tex: .6, border: .5, ink: '#6B5A48', sw: .5, br: 'HB' });
  for (let i = 0; i < 7; i++) { const y = 520 + i * 62; sketch('rib' + i, [[250, y + 40], [400, y - 10], [520, y + 20]], .5, '#B9AB93', '2H'); sketch('ribr' + i, [[W - 250, y + 40], [W - 400, y - 10], [W - 520, y + 20]], .5, '#B9AB93', '2H'); }
  const lk = seg(lt, 0, 1.2);
  stillSeed('lungL'); drawOn(LUNG_L, lk, 1.6, '#3A3029', 'charcoal');
  stillSeed('lungR'); drawOn(LUNG_R, lk, 1.6, '#3A3029', 'charcoal');
  if (lt > .7) { shade('lsL', LUNG_L, '#6A5A4E', 11, 60, 'HB', .6, .5); shade('lsR', LUNG_R, '#6A5A4E', 11, 120, 'HB', .6, .5); }
  const tree = [[[540, 290], [540, 440]], [[540, 440], [470, 520]], [[540, 440], [610, 520]], [[470, 520], [420, 600]], [[470, 520], [460, 640]], [[610, 520], [660, 600]], [[610, 520], [620, 650]], [[420, 600], [380, 700]], [[660, 600], [700, 700]]];
  tree.forEach((s, i) => { stillSeed('br' + i); drawOn(s, seg(lt, .3 + i * .05, .9 + i * .05), i ? 1 : 1.6, '#3A3029', '2B'); });
  [[380, 640, 58], [430, 790, 44], [690, 580, 50], [720, 800, 66], [640, 700, 32]].forEach(([x, y, r], i) => {
    const g = ease(seg(lt, .9 + i * .22, 2.0 + i * .22)); if (g > 0) wc('spot' + i, ellPts(x, y, r * g, r * .8 * g, 22), '#7A2E22', 160, { bleed: .3, tex: .7, border: .7 });
  });
  letter('tuberculosis', 540, 230, 92, '#7A2E22', { font: `92px ${JOURNAL}`, ink: false, alpha: seg(lt, 1.0, 1.4), rot: -.03 });
  camEnd();
  if (lt > 2.6) {  // a fresh page slides up over the lungs and the quote is written as the voice reaches each line
    flushLetters();
    const k = ease(seg(lt, 2.6, 2.95)), Q = [2.75, 3.3, 3.85, 4.6, 6.1, 6.8];
    wc('qpage', rrPts(60, 150 + (1 - k) * 1300, W - 120, 1150, 10), '#F2E8D2', 200, { wash: '#F3E9D4', washOp: 255, tex: .6, border: .5, ink: '#6B5A48', sw: .5, br: 'HB' });
    QUOTE.forEach((line, i) => {
      const a = seg(lt, Q[i], Q[i] + .35);
      if (a > 0) letter(line, 130, 330 + i * 120, 74, i === 4 ? '#7A2E22' : '#2B2233', { font: `74px ${JOURNAL}`, align: 'left', ink: false, alpha: a, rot: -.015 });
    });
    if (lt > 6.4) { stillSeed('under'); drawOn([[130, 852], [560, 846]], seg(lt, 6.4, 6.8), 1.6, '#7A2E22', 'rotring'); }
    letter('- A.M.', 900, 1120, 70, '#3A3029', { font: `70px ${JOURNAL}`, ink: false, alpha: seg(lt, 7.3, 7.7) });
  }
}

shots([[14, A1], [19, A2], [25, A3]]);
