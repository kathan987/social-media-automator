// Explainer 3D layer: Three.js 0.187 drawn from HyperFrames' hf-seek time (deterministic, no rAF clock).
// Reads window.__three = [{kind: "timeline" | "jet", start, end, labels: ["TOP|BOTTOM|#hex", ...]}] (seconds).
// Used by tools/sticker_short.py when a spec has "three" (docs/formats.md).
import * as THREE from "./three/three.module.js";

const SPECS = window.__three || [];
const canvas = document.getElementById("three");
const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(1080, 1920, false);
renderer.setClearColor(0x000000, 0);
renderer.outputColorSpace = THREE.SRGBColorSpace;

const clamp = (x) => Math.min(Math.max(x, 0), 1);
const ease = (x) => 1 - Math.pow(1 - clamp(x), 3);

function lit(scene) {
  scene.add(new THREE.HemisphereLight(0xbfd4ff, 0x20160c, 0.9));
  const key = new THREE.DirectionalLight(0xffd9a8, 2.2);  // warm key
  key.position.set(4, 6, 5);
  const rim = new THREE.DirectionalLight(0x7fb2ff, 1.4);  // cool rim
  rim.position.set(-5, 2, -4);
  scene.add(key, rim);
}

function roundRect(g, x, y, w, h, r) {
  g.beginPath();
  g.moveTo(x + r, y);
  g.arcTo(x + w, y, x + w, y + h, r);
  g.arcTo(x + w, y + h, x, y + h, r);
  g.arcTo(x, y + h, x, y, r);
  g.arcTo(x, y, x + w, y, r);
  g.closePath();
}

function tag(top, bottom, color) {
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 256;
  const g = c.getContext("2d");
  roundRect(g, 10, 10, 492, 236, 36);
  g.fillStyle = "rgba(10,10,10,.85)";
  g.fill();
  g.lineWidth = 10;
  g.strokeStyle = color;
  g.stroke();
  g.textAlign = "center";
  g.fillStyle = color;
  g.font = "64px Bebas";
  g.fillText(top, 256, 100);
  g.fillStyle = "#ffffff";
  g.font = "96px Bebas";
  g.fillText(bottom, 256, 205);
  const map = new THREE.CanvasTexture(c);
  map.colorSpace = THREE.SRGBColorSpace;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map, transparent: true, depthTest: false }));
  s.scale.set(2.0, 1.0, 1);  // portrait frame: about 3.4 units wide at the camera's working distance
  return s;
}

// A gold ribbon running into depth with one glowing marker per label; the camera dives along it (an order of events).
function timeline(spec) {
  const scene = new THREE.Scene();
  lit(scene);
  const camera = new THREE.PerspectiveCamera(42, 1080 / 1920, 0.1, 100);
  const n = spec.labels.length, gap = 3.4;
  const ribbon = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.08, gap * (n - 1) + 3),
    new THREE.MeshStandardMaterial({ color: 0xd9a441, metalness: 0.6, roughness: 0.45, emissive: 0x2a1a00 }));
  ribbon.position.z = -gap * (n - 1) / 2;
  scene.add(ribbon);
  const marks = spec.labels.map((label, i) => {
    const [top, bottom, hex] = label.split("|");
    const color = hex || "#ffd84a";
    const orb = new THREE.Mesh(new THREE.SphereGeometry(0.3, 32, 16),
      new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.4, roughness: 0.45 }));
    orb.position.set(0, 0.32, -i * gap);
    const t = tag(top, bottom || "", color);
    t.position.set(i % 2 ? 0.4 : -0.4, 1.55, -i * gap);  // staggered so the next label never hides behind this one
    scene.add(orb, t);
    return { orb, t };
  });
  function update(t, dur) {
    // Equal time per marker: glide to it in the first 40% of its slot, then hold so the label can be read.
    const slot = dur / n, i0 = Math.min(Math.floor(t / slot), n - 1), u = (t - i0 * slot) / slot;
    const focus = i0 === 0 ? 0 : i0 - 1 + ease(u / 0.4);
    camera.position.set(Math.sin(focus * 1.1) * 0.6, 3.0, 8.5 - focus * gap);  // ~8.5 units behind the marker in focus
    camera.lookAt(0, 2.5, camera.position.z - 8.5);  // aim high so the ribbon and labels sit below the top captions
    marks.forEach((m, i) => {
      const k = Math.min(ease((focus - i + 0.6) / 0.3) * ease(t / 0.3),  // pops in as the camera arrives...
                         1 - ease((focus - i - 0.45) / 0.25));           // ...and fades before the camera flies through it
      m.orb.scale.setScalar(Math.max(k, 0.001));
      m.orb.rotation.y = t * 2;
      m.t.material.opacity = k;
    });
  }
  return { scene, camera, update };
}

// A low-poly fighter jet that banks across the portrait frame, bottom-left to top-right ("fighter pilot").
function jet() {
  const scene = new THREE.Scene();
  lit(scene);
  const camera = new THREE.PerspectiveCamera(35, 1080 / 1920, 0.1, 100);
  camera.position.set(0, 0, 12);
  const grey = new THREE.MeshStandardMaterial({ color: 0x8c96a3, metalness: 0.7, roughness: 0.45 });
  const dark = new THREE.MeshStandardMaterial({ color: 0x2b3038, metalness: 0.5, roughness: 0.5 });
  const glass = new THREE.MeshStandardMaterial({ color: 0x1d3b5c, metalness: 0.2, roughness: 0.15 });
  const plane = new THREE.Group();
  const body = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.36, 4, 24), grey);
  body.rotation.z = Math.PI / 2;
  const nose = new THREE.Mesh(new THREE.ConeGeometry(0.28, 1.2, 24), grey);
  nose.rotation.z = -Math.PI / 2;
  nose.position.x = 2.6;
  const canopy = new THREE.Mesh(new THREE.SphereGeometry(0.3, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2), glass);
  canopy.position.set(1.2, 0.22, 0);
  canopy.scale.set(1.8, 0.8, 0.9);
  const wing = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.06, 4.2), grey);
  wing.position.x = -0.2;
  const fin = new THREE.Mesh(new THREE.BoxGeometry(0.9, 1.1, 0.06), dark);
  fin.position.set(-1.7, 0.6, 0);
  const stab = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.05, 1.6), grey);
  stab.position.set(-1.8, 0.05, 0);
  const flame = new THREE.Mesh(new THREE.ConeGeometry(0.22, 0.9, 16),
    new THREE.MeshBasicMaterial({ color: 0xffa040, transparent: true, opacity: 0.85 }));
  flame.rotation.z = Math.PI / 2;
  flame.position.x = -2.45;
  plane.add(body, nose, canopy, wing, fin, stab, flame);
  plane.scale.setScalar(0.85);
  scene.add(plane);
  function update(t, dur) {
    const p = clamp(t / dur);
    plane.position.set(-3.6 + p * 7.2, -4.2 + p * 7.6 + Math.sin(p * Math.PI) * 0.8, 0);
    plane.rotation.set(0.35 + Math.sin(p * 5) * 0.25, 0.55 - p * 0.5, 0.55);
    flame.scale.setScalar(0.8 + 0.25 * Math.sin(t * 40));
  }
  return { scene, camera, update };
}

const KINDS = { timeline, jet };
let built = [];

function renderAt(t) {
  const s = built.find((b) => t >= b.start && t < b.end);
  if (!s) {
    renderer.clear();
    return;
  }
  s.update(t - s.start, s.end - s.start);
  renderer.render(s.scene, s.camera);
}

window.addEventListener("hf-seek", (e) => renderAt(e.detail.time));
document.fonts.load("96px Bebas").then(() => {
  built = SPECS.map((s) => ({ ...s, ...KINDS[s.kind](s) }));
  renderAt(0);
  if (window.__threeReady) window.__threeReady();
});
