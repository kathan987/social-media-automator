"""One-time setup after `npm install`: copy Three.js, GSAP and the Bebas Neue font into scenes/explainer-scene/assets
so HyperFrames renders offline. Third-party files are copied, never committed (see .gitignore).
  python tools/setup_scene.py"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENE = ROOT / "scenes" / "explainer-scene" / "assets"
NM = ROOT / "node_modules"
copies = [(NM / "three" / "build" / "three.module.js", SCENE / "three" / "three.module.js"),
          (NM / "three" / "build" / "three.core.js", SCENE / "three" / "three.core.js"),
          (NM / "gsap" / "dist" / "gsap.min.js", SCENE / "gsap.min.js"),
          (ROOT / "assets" / "fonts" / "BebasNeue-Regular.ttf", SCENE / "fonts" / "BebasNeue-Regular.ttf")]
missing = [str(src.relative_to(ROOT)) for src, _ in copies if not src.exists()]
if missing:
    sys.exit("Missing: " + ", ".join(missing) + "\nRun `npm install` and put BebasNeue-Regular.ttf (Google Fonts) in assets/fonts/.")
for src, dst in copies:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print("copied", dst.relative_to(ROOT))
