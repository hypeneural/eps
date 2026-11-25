/* Optional orbital read-only 3D renderer (Three.js r180 local vendor, zero CDN). */
import * as THREE from "three";
import { OrbitControls } from "./OrbitControls.js";

function createEpsTextures() {
  const size = 128;
  const colCanvas = document.createElement("canvas");
  colCanvas.width = size;
  colCanvas.height = size;
  const cc = colCanvas.getContext("2d");

  const bumpCanvas = document.createElement("canvas");
  bumpCanvas.width = size;
  bumpCanvas.height = size;
  const bc = bumpCanvas.getContext("2d");

  if (cc && bc) {
    cc.fillStyle = "#f2f6f8";
    cc.fillRect(0, 0, size, size);
    bc.fillStyle = "#707070";
    bc.fillRect(0, 0, size, size);

    /* Deterministic pseudo-random cellular EPS bead pattern */
    let seed = 1337;
    const rand = () => {
      seed = (seed * 16807) % 2147483647;
      return (seed - 1) / 2147483646;
    };
    const step = 16;
    for (let gy = 0; gy < size; gy += step) {
      for (let gx = 0; gx < size; gx += step) {
        const cx = gx + step * 0.5 + (rand() - 0.5) * 4.5;
        const cy = gy + step * 0.5 + (rand() - 0.5) * 4.5;
        const r = 6.2 + rand() * 2.4;

        /* Tile wrap across edges for seamless repeat */
        for (const ox of [-size, 0, size]) {
          for (const oy of [-size, 0, size]) {
            const x = cx + ox;
            const y = cy + oy;
            if (x < -r || x > size + r || y < -r || y > size + r) continue;

            const cg = cc.createRadialGradient(x - r * 0.28, y - r * 0.28, r * 0.1, x, y, r);
            cg.addColorStop(0, "#ffffff");
            cg.addColorStop(0.75, "#eef3f6");
            cg.addColorStop(1, "#cfdce3");
            cc.beginPath();
            cc.arc(x, y, r, 0, Math.PI * 2);
            cc.fillStyle = cg;
            cc.fill();
            cc.strokeStyle = "rgba(164, 184, 196, 0.45)";
            cc.lineWidth = 0.8;
            cc.stroke();

            const bg = bc.createRadialGradient(x, y, r * 0.1, x, y, r);
            bg.addColorStop(0, "#f2f2f2");
            bg.addColorStop(0.78, "#bcbcbc");
            bg.addColorStop(1, "#4a4a4a");
            bc.beginPath();
            bc.arc(x, y, r, 0, Math.PI * 2);
            bc.fillStyle = bg;
            bc.fill();
          }
        }
      }
    }
  }

  const map = new THREE.CanvasTexture(colCanvas);
  map.wrapS = THREE.RepeatWrapping;
  map.wrapT = THREE.RepeatWrapping;
  map.colorSpace = THREE.SRGBColorSpace;
  map.repeat.set(4, 2);

  const bumpMap = new THREE.CanvasTexture(bumpCanvas);
  bumpMap.wrapS = THREE.RepeatWrapping;
  bumpMap.wrapT = THREE.RepeatWrapping;
  bumpMap.repeat.set(4, 2);

  return { map, bumpMap };
}

export function createCutThree(host, data, onFailure) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
  renderer.setClearColor(0x0f1f29);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.08;
  host.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0f1f29);

  const camera = new THREE.PerspectiveCamera(34, 1, 0.01, 100);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = false;
  controls.minDistance = 0.25;
  controls.maxDistance = 8.0;
  controls.maxPolarAngle = Math.PI * 0.88;

  const b = data.bbox;
  const span = Math.max(b.width, b.height, 1);
  const depth = 0.42;
  const width = Math.max(b.width / span, 0.05);
  const rawHeight = b.height / span;
  const height = Math.max(rawHeight, 0.055);
  const gap = Math.max(height * 0.62, 0.065);
  const yLift = rawHeight < 0.01 ? height * 0.5 : 0;

  const X = (x) => (x - b.x_min - b.width / 2) / span;
  const Y = (y) => (y - b.y_min) / span + yLift;
  const point = (p, z = 0, o = 0) => new THREE.Vector3(X(p[0]), Y(p[1]) + o, z);

  /* 3-point industrial studio lighting */
  const hemi = new THREE.HemisphereLight(0xf6fbff, 0x203543, 1.65);
  scene.add(hemi);
  const key = new THREE.DirectionalLight(0xffffff, 1.65);
  key.position.set(1.8, 2.9, 2.4);
  scene.add(key);
  const rim = new THREE.DirectionalLight(0x9bd1eb, 0.75);
  rim.position.set(-2.0, 1.2, -1.6);
  scene.add(rim);

  const epsTex = createEpsTextures();
  const makeMat = (color, opts = {}) =>
    new THREE.MeshStandardMaterial({
      color,
      roughness: opts.roughness ?? 0.82,
      metalness: opts.metalness ?? 0.04,
      transparent: (opts.opacity ?? 1) < 1,
      opacity: opts.opacity ?? 1,
      depthWrite: opts.depthWrite ?? ((opts.opacity ?? 1) === 1),
      map: opts.map || null,
      bumpMap: opts.bumpMap || null,
      bumpScale: opts.bumpScale ?? 0.004,
      emissive: opts.emissive ?? 0x000000,
      emissiveIntensity: opts.emissiveIntensity ?? 0,
    });

  const frameMat = makeMat(0x3a5a6d, { roughness: 0.45, metalness: 0.35 });
  const bedMat = makeMat(0x1f3644, { roughness: 0.62, metalness: 0.22 });
  const railRedMat = makeMat(0xd62828, { roughness: 0.4, metalness: 0.15 });
  const carriageMat = makeMat(0xe5eff5, { roughness: 0.35, metalness: 0.45 });
  const stockMat = makeMat(0xf4f8fa, {
    roughness: 0.9,
    opacity: 0.38,
    depthWrite: false,
    map: epsTex.map,
    bumpMap: epsTex.bumpMap,
    bumpScale: 0.004,
  });

  /* Coherent schematic SCARA gantry frame */
  const frame = new THREE.Group();
  scene.add(frame);

  function addBox(w, h, d, x, y, z, mat, parent) {
    const geo = new THREE.BoxGeometry(w, h, d);
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(x, y, z);
    parent.add(mesh);
    return mesh;
  }

  function addBoxWithEdges(w, h, d, x, y, z, mat, edgeColor, parent) {
    const mesh = addBox(w, h, d, x, y, z, mat, parent);
    const edges = new THREE.LineSegments(
      new THREE.EdgesGeometry(mesh.geometry),
      new THREE.LineBasicMaterial({ color: edgeColor, transparent: true, opacity: 0.55 })
    );
    mesh.add(edges);
    return mesh;
  }

  const colX = width / 2 + 0.095;
  const colZFront = -0.065;
  const colZBack = depth + 0.065;
  const frameTopY = height + gap + 0.14;
  const bedTopY = -0.032;
  const bedThick = 0.044;

  /* Cutting bed + reference grid */
  addBoxWithEdges(width + 0.24, bedThick, depth + 0.2, 0, bedTopY - bedThick / 2, depth / 2, bedMat, 0x5c8499, frame);
  const gridSize = Math.max(width + 0.35, depth + 0.35);
  const grid = new THREE.GridHelper(gridSize, 14, 0x487085, 0x223b4a);
  grid.position.set(0, bedTopY + 0.001, depth / 2);
  frame.add(grid);

  /* Four upright columns + side rails */
  const colH = frameTopY - bedTopY;
  for (const sx of [-colX, colX]) {
    for (const sz of [colZFront, colZBack]) {
      addBox(0.026, colH, 0.026, sx, bedTopY + colH / 2, sz, frameMat, frame);
    }
    addBox(0.022, 0.022, colZBack - colZFront, sx, frameTopY, depth / 2, frameMat, frame);
  }
  /* Front & rear upper gantry bridge beams + Iso Nunes red rail */
  for (const sz of [colZFront, colZBack]) {
    addBox(colX * 2 + 0.026, 0.028, 0.026, 0, frameTopY, sz, frameMat, frame);
  }
  addBox(colX * 2 - 0.02, 0.009, 0.03, 0, frameTopY, colZFront, railRedMat, frame);

  /* Moving X carriage on front bridge beam */
  const xCarriage = addBox(0.046, 0.036, 0.042, 0, frameTopY, colZFront, carriageMat, frame);

  /* Translucent white EPS stock block (dual vs single height) */
  const stockDual = addBoxWithEdges(width + 0.035, height + gap + 0.035, depth, 0, (height + gap) / 2, depth / 2, stockMat, 0xa8c6d6, scene);
  const stockSingle = addBoxWithEdges(width + 0.035, height + 0.035, depth, 0, height / 2, depth / 2, stockMat, 0xa8c6d6, scene);

  /* Wire groups (Wire 1 nominal + Wire 2 schematic parallel) */
  const groups = [new THREE.Group(), new THREE.Group()];
  groups.forEach((g) => scene.add(g));

  const wires = [];
  const segments = data.segments;
  const wireRadius = Math.max(0.0042, Math.min(0.0062, height * 0.055));

  groups.forEach((g, k) => {
    const o = k ? gap : 0;
    const coreColor = k ? 0xff8a5b : 0xffd166;
    const glowColor = k ? 0xff5a30 : 0xff9d2e;
    const cutColor = k ? 0xff9e70 : 0x52e6c8;

    const verts = [];
    const faces = [];
    segments.forEach((s) => {
      const a = point(s.start, 0, o);
      const bPt = point(s.end, 0, o);
      const c = point(s.end, depth, o);
      const d = point(s.start, depth, o);
      verts.push(...a.toArray(), ...bPt.toArray());
      for (const v of [a, bPt, c, a, c, d]) faces.push(...v.toArray());
    });

    const lines = new THREE.BufferGeometry();
    lines.setAttribute("position", new THREE.Float32BufferAttribute(verts, 3));
    const remaining = new THREE.LineSegments(
      lines,
      new THREE.LineBasicMaterial({ color: k ? 0xcfa38c : 0x9ab8c8, transparent: true, opacity: 0.48 })
    );
    g.add(remaining);

    const doneGeom = lines.clone();
    const done = new THREE.LineSegments(doneGeom, new THREE.LineBasicMaterial({ color: cutColor }));
    g.add(done);

    const surfaceGeom = new THREE.BufferGeometry();
    surfaceGeom.setAttribute("position", new THREE.Float32BufferAttribute(faces, 3));
    const surface = new THREE.Mesh(
      surfaceGeom,
      new THREE.MeshBasicMaterial({ color: cutColor, side: THREE.DoubleSide, transparent: true, opacity: 0.34, depthWrite: false })
    );
    g.add(surface);

    /* Volumetric glowing hotwire filament (cylinder along Z + outer glow sheath + metallic holders) */
    const wireRig = new THREE.Group();
    const cylCore = new THREE.Mesh(
      new THREE.CylinderGeometry(wireRadius, wireRadius, depth + 0.04, 12),
      makeMat(coreColor, { roughness: 0.2, emissive: glowColor, emissiveIntensity: 1.4 })
    );
    cylCore.rotation.x = Math.PI / 2;
    cylCore.position.z = depth / 2;
    wireRig.add(cylCore);

    const cylGlow = new THREE.Mesh(
      new THREE.CylinderGeometry(wireRadius * 2.2, wireRadius * 2.2, depth + 0.02, 12),
      new THREE.MeshBasicMaterial({ color: glowColor, transparent: true, opacity: 0.28, depthWrite: false })
    );
    cylGlow.rotation.x = Math.PI / 2;
    cylGlow.position.z = depth / 2;
    wireRig.add(cylGlow);

    for (const hz of [-0.025, depth + 0.025]) {
      const holder = new THREE.Mesh(new THREE.BoxGeometry(0.022, 0.022, 0.028), carriageMat);
      holder.position.z = hz;
      wireRig.add(holder);
    }
    g.add(wireRig);

    /* Synchronized side Y-guide sliders on left/right front columns */
    const sliderMat = makeMat(coreColor, { roughness: 0.35, emissive: glowColor, emissiveIntensity: 0.35 });
    const leftSlider = addBox(0.038, 0.022, 0.034, -colX, o, colZFront, sliderMat, frame);
    const rightSlider = addBox(0.038, 0.022, 0.034, colX, o, colZFront, sliderMat, frame);

    const partialGeom = new THREE.BufferGeometry();
    partialGeom.setAttribute("position", new THREE.Float32BufferAttribute(new Float32Array(6), 3));
    const partial = new THREE.Line(partialGeom, new THREE.LineBasicMaterial({ color: cutColor }));
    partial.frustumCulled = false;
    g.add(partial);

    const partialSurfaceGeom = new THREE.BufferGeometry();
    partialSurfaceGeom.setAttribute("position", new THREE.Float32BufferAttribute(new Float32Array(18), 3));
    const partialSurface = new THREE.Mesh(
      partialSurfaceGeom,
      new THREE.MeshBasicMaterial({ color: cutColor, side: THREE.DoubleSide, transparent: true, opacity: 0.34, depthWrite: false })
    );
    partialSurface.frustumCulled = false;
    g.add(partialSurface);

    wires.push({
      o,
      remaining,
      doneGeom,
      surfaceGeom,
      wireRig,
      leftSlider,
      rightSlider,
      partialGeom,
      partialSurfaceGeom,
    });
  });

  /* Demonstrable nominal extruded EPS regions (shown only in "Ver resultado nominal") */
  const nominal = new THREE.Group();
  scene.add(nominal);
  const regions = data.regions;
  if (regions && regions.demonstrable) {
    [regions.lower_region_xy, regions.upper_region_xy].forEach((ring, i) => {
      const shape = new THREE.Shape();
      ring.forEach((p, j) => {
        const x = X(p[0]);
        const y = Y(p[1]);
        if (j) shape.lineTo(x, y);
        else shape.moveTo(x, y);
      });
      shape.closePath();
      const geo = new THREE.ExtrudeGeometry(shape, { depth, bevelEnabled: false, steps: 1 });
      const mat = i
        ? makeMat(0x7c9eb2, { roughness: 0.78, opacity: 0.52, depthWrite: false })
        : makeMat(0xf7fafc, { roughness: 0.88, map: epsTex.map, bumpMap: epsTex.bumpMap, bumpScale: 0.005 });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.y = i ? 0.022 : -0.014;
      const edge = new THREE.LineSegments(
        new THREE.EdgesGeometry(geo, 22),
        new THREE.LineBasicMaterial({ color: i ? 0x9ec0d4 : 0x577b8f, transparent: true, opacity: i ? 0.5 : 0.45 })
      );
      mesh.add(edge);
      nominal.add(mesh);
    });
  }
  nominal.visible = false;

  let lastFront = false;
  function draw() {
    renderer.render(scene, camera);
  }

  function fit(front = false) {
    lastFront = Boolean(front);
    const totalW = colX * 2 + 0.08;
    const totalH = Math.max(frameTopY - bedTopY + 0.06, 0.28);
    const centerY = (bedTopY + frameTopY) * 0.48;
    controls.target.set(0, centerY, depth / 2);

    const vFov = THREE.MathUtils.degToRad(camera.fov);
    const aspect = Math.max(0.5, camera.aspect || 1.5);
    const hFov = 2 * Math.atan(Math.tan(vFov / 2) * aspect);
    const distV = (totalH * 0.56) / Math.tan(vFov / 2);
    const distH = (totalW * 0.56) / Math.tan(hFov / 2);
    const dist = Math.max(distV, distH, 0.65) * (lastFront ? 1.2 : 1.34) + depth * 0.85;

    if (lastFront) {
      camera.position.set(0, centerY, depth / 2 + dist);
    } else {
      const az = THREE.MathUtils.degToRad(26);
      const el = THREE.MathUtils.degToRad(20);
      camera.position.set(
        Math.sin(az) * Math.cos(el) * dist,
        centerY + Math.sin(el) * dist,
        depth / 2 + Math.cos(az) * Math.cos(el) * dist
      );
    }
    controls.update();
    draw();
  }

  function resize() {
    const rect = host.getBoundingClientRect();
    if (rect.width && rect.height) {
      renderer.setSize(rect.width, rect.height, false);
      camera.aspect = rect.width / rect.height;
      camera.updateProjectionMatrix();
      draw();
    }
  }

  controls.addEventListener("change", draw);
  const lost = (e) => {
    e.preventDefault();
    onFailure();
  };
  renderer.domElement.addEventListener("webglcontextlost", lost);

  resize();
  fit(false);

  function setAttr(geo, points) {
    const a = geo.getAttribute("position");
    a.array.set(points.flatMap((v) => v.toArray()));
    a.needsUpdate = true;
  }

  function update(pos, options) {
    const showNominal = Boolean(options.result && regions && regions.demonstrable);
    frame.visible = options.machine && !showNominal;
    stockDual.visible = options.stock && options.dual && !showNominal;
    stockSingle.visible = options.stock && !options.dual && !showNominal;
    nominal.visible = showNominal;
    groups[0].visible = !showNominal;
    groups[1].visible = options.dual && !showNominal;

    xCarriage.position.x = X(pos.p[0]);
    wires.forEach((v, k) => {
      v.remaining.visible = options.path;
      v.leftSlider.visible = options.machine && (!k || options.dual);
      v.rightSlider.visible = options.machine && (!k || options.dual);
      v.doneGeom.setDrawRange(0, pos.i * 2);
      v.surfaceGeom.setDrawRange(0, pos.i * 6);

      const a = point(segments[pos.i].start, 0, v.o);
      const bPt = point(pos.p, 0, v.o);
      const c = point(pos.p, depth, v.o);
      const d = point(segments[pos.i].start, depth, v.o);

      v.wireRig.position.set(bPt.x, bPt.y, 0);
      v.leftSlider.position.y = bPt.y;
      v.rightSlider.position.y = bPt.y;
      setAttr(v.partialGeom, [a, bPt]);
      setAttr(v.partialSurfaceGeom, [a, bPt, c, a, c, d]);
    });
    draw();
  }

  function dispose() {
    controls.dispose();
    renderer.domElement.removeEventListener("webglcontextlost", lost);
    epsTex.map.dispose();
    epsTex.bumpMap.dispose();
    scene.traverse((o) => {
      if (o.geometry) o.geometry.dispose();
      if (o.material) {
        if (Array.isArray(o.material)) o.material.forEach((m) => m.dispose());
        else o.material.dispose();
      }
    });
    renderer.dispose();
    renderer.domElement.remove();
  }

  return { update, resize, fit, dispose };
}
