/* Shared, read-only Canvas 2D renderer: no WebGL, CDN, controller or external deps. */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var root = $("cut-player");

  /* Library filter mode on /conferencia/index.html */
  if (!root) {
    var search = $("cut-search"), category = $("cut-category");
    if (search && category) {
      var filter = function () {
        var count = 0;
        var q = search.value.trim().toLowerCase();
        document.querySelectorAll(".review-card").forEach(function (card) {
          var match = (!category.value || card.dataset.category === category.value) &&
            card.textContent.toLowerCase().indexOf(q) !== -1;
          card.hidden = !match;
          if (match) count++;
        });
        var counter = $("cut-count");
        if (counter) counter.textContent = count + (count === 1 ? " modelo" : " modelos");
      };
      search.addEventListener("input", filter);
      category.addEventListener("change", filter);
      filter();
    }
    return;
  }

  var canvas = $("cut-canvas");
  var ctx = canvas && canvas.getContext ? canvas.getContext("2d") : null;
  if (!ctx) return;

  /* Lightweight procedural EPS bead foam texture (cached offscreen pattern) */
  function makeEpsPattern(alpha) {
    var tile = document.createElement("canvas");
    tile.width = 44;
    tile.height = 44;
    var tc = tile.getContext("2d");
    if (!tc) return "rgba(232,242,247," + alpha + ")";
    tc.fillStyle = "rgba(236,244,248," + alpha + ")";
    tc.fillRect(0, 0, 44, 44);
    var beads = [
      [7, 7, 5.2], [18, 6, 4.4], [30, 8, 5.0], [40, 6, 4.2],
      [4, 18, 4.6], [14, 17, 5.4], [25, 19, 4.8], [37, 17, 5.1],
      [9, 29, 5.1], [20, 30, 4.6], [32, 29, 5.3], [42, 30, 4.3],
      [5, 40, 4.4], [16, 40, 4.9], [28, 40, 4.5], [39, 40, 5.0]
    ];
    beads.forEach(function (bd) {
      tc.beginPath();
      tc.arc(bd[0], bd[1], bd[2], 0, Math.PI * 2);
      tc.fillStyle = "rgba(255,255,255," + Math.min(0.6, alpha * 0.65) + ")";
      tc.fill();
      tc.strokeStyle = "rgba(138,168,184," + Math.min(0.55, alpha * 0.72) + ")";
      tc.lineWidth = 0.85;
      tc.stroke();
      tc.beginPath();
      tc.arc(bd[0] - bd[2] * 0.28, bd[1] - bd[2] * 0.28, bd[2] * 0.28, 0, Math.PI * 2);
      tc.fillStyle = "rgba(255,255,255," + Math.min(0.75, alpha * 0.85) + ")";
      tc.fill();
    });
    return ctx.createPattern(tile, "repeat") || ("rgba(232,242,247," + alpha + ")");
  }

  function init(data) {
    if (
      data.schema !== 1 ||
      data.tap_sha256 !== root.dataset.hash ||
      !Array.isArray(data.segments) ||
      !data.segments.length ||
      !(data.distance_mm > 0)
    ) {
      throw Error("Invalid simulation");
    }

    var seg = data.segments;
    var total = data.distance_mm;
    var b = data.bbox;
    var regions = data.regions && data.regions.demonstrable ? data.regions : null;
    var dist = 0, playing = false, raf = 0, last = 0, w = 0, h = 0;
    var epsBlockPat = makeEpsPattern(0.24);
    var epsLowerPat = makeEpsPattern(0.84);
    var fmt = function (n) { return n.toLocaleString("pt-BR", { maximumFractionDigits: 1 }); };

    if (!regions && $("cut-regions")) {
      $("cut-regions").checked = false;
      $("cut-regions").disabled = true;
    }

    function locate(d) {
      var lo = 0, hi = seg.length - 1;
      while (lo < hi) {
        var mid = (lo + hi) >> 1;
        if (seg[mid].end_distance_mm < d) lo = mid + 1;
        else hi = mid;
      }
      var s = seg[lo];
      var start = lo ? seg[lo - 1].end_distance_mm : 0;
      var denom = Math.max(1e-9, s.end_distance_mm - start);
      var f = Math.max(0, Math.min(1, (d - start) / denom));
      return {
        i: lo,
        p: [
          s.start[0] + (s.end[0] - s.start[0]) * f,
          s.start[1] + (s.end[1] - s.start[1]) * f
        ]
      };
    }

    function paint() {
      if (!w || !h) return;
      var pos = locate(dist);
      var front = $("cut-view").value === "front";
      var dual = $("cut-dual").checked;
      var stock = $("cut-stock").checked;
      var showRegions = Boolean(regions && $("cut-regions") && $("cut-regions").checked);
      var showMachine = !$("cut-machine") || $("cut-machine").checked;
      var showPath = $("cut-path").checked;

      var span = Math.max(1, b.width, b.height);
      var pad = Math.max(b.height * 0.14, span * 0.032);
      var offset = dual ? Math.max(b.height * 0.62, span * 0.04) : 0;
      var depth = front ? 0 : span * 0.24;
      var angle = Number($("cut-angle").value);
      var dx = depth * angle;
      var dy = depth * 0.46;

      var framePadX = showMachine ? Math.max(span * 0.07, 26) : 0;
      var framePadTop = showMachine ? Math.max(b.height * 0.42, span * 0.055) : 0;
      var framePadBot = showMachine ? Math.max(b.height * 0.34, span * 0.045) : 0;

      var worldW = b.width + 2 * (pad + framePadX) + Math.abs(dx);
      var worldH = b.height + offset + 2 * pad + framePadTop + framePadBot + dy;
      var marginX = Math.max(20, Math.min(36, w * 0.05));
      var marginY = 66;
      var scale = Math.min(
        (w - marginX * 2) / Math.max(1, worldW),
        (h - marginY) / Math.max(1, worldH)
      ) * Number($("cut-zoom").value);

      var cx = b.x_min + b.width / 2 + dx / 2;
      var cy = b.y_min + (b.height + offset + framePadTop - framePadBot) / 2 + dy / 2;
      var ox = w / 2 - cx * scale;
      var oy = h / 2 + cy * scale + 6;

      function proj(p, z, o) {
        return [ox + (p[0] + z * dx) * scale, oy - (p[1] + (o || 0) + z * dy) * scale];
      }

      function polygon(points, fill, stroke, lw) {
        ctx.beginPath();
        for (var i = 0; i < points.length; i++) {
          if (i) ctx.lineTo(points[i][0], points[i][1]);
          else ctx.moveTo(points[i][0], points[i][1]);
        }
        ctx.closePath();
        if (fill) {
          ctx.fillStyle = fill;
          ctx.fill();
        }
        if (stroke) {
          ctx.strokeStyle = stroke;
          ctx.lineWidth = lw || 1;
          ctx.stroke();
        }
      }

      function segLine(a, c, color, width, dash) {
        ctx.beginPath();
        if (dash) ctx.setLineDash(dash);
        ctx.moveTo(a[0], a[1]);
        ctx.lineTo(c[0], c[1]);
        ctx.strokeStyle = color;
        ctx.lineWidth = width;
        ctx.lineCap = "round";
        ctx.stroke();
        if (dash) ctx.setLineDash([]);
      }

      function pillLabel(text, x, y, bg, fg, border) {
        ctx.save();
        ctx.font = "bold 11px system-ui, -apple-system, Segoe UI, Arial, sans-serif";
        var tw = ctx.measureText(text).width;
        var pw = tw + 12, ph = 19;
        var px = Math.max(8, Math.min(w - pw - 8, x));
        var py = Math.max(38, Math.min(h - ph - 26, y));
        ctx.fillStyle = bg;
        ctx.strokeStyle = border;
        ctx.lineWidth = 1;
        ctx.beginPath();
        if (ctx.roundRect) ctx.roundRect(px, py, pw, ph, 5);
        else ctx.rect(px, py, pw, ph);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = fg;
        ctx.fillText(text, px + 6, py + 13);
        ctx.restore();
      }

      /* 1. Studio backdrop + subtle technical grid */
      var bgGrad = ctx.createLinearGradient(0, 0, 0, h);
      bgGrad.addColorStop(0, "#0c1821");
      bgGrad.addColorStop(1, "#162c3a");
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, w, h);

      ctx.strokeStyle = "rgba(130, 174, 198, 0.065)";
      ctx.lineWidth = 1;
      var gridStep = Math.max(24, Math.min(48, w / 22));
      ctx.beginPath();
      for (var gx = (w % gridStep) / 2; gx < w; gx += gridStep) {
        ctx.moveTo(gx, 0); ctx.lineTo(gx, h);
      }
      for (var gy = (h % gridStep) / 2; gy < h; gy += gridStep) {
        ctx.moveTo(0, gy); ctx.lineTo(w, gy);
      }
      ctx.stroke();

      var x0 = b.x_min - pad, x1 = b.x_max + pad;
      var y0 = b.y_min - pad * 0.45, y1 = b.y_max + offset + pad;
      var mx0 = x0 - framePadX, mx1 = x1 + framePadX;
      var myBot = y0 - framePadBot * 0.85, myTop = y1 + framePadTop * 0.88;
      var colW = Math.max(framePadX * 0.24, span * 0.014);

      /* 2. Schematic SCARA hotwire machine — rear frame + table bed */
      if (showMachine) {
        var tableTop = y0 - framePadBot * 0.08;
        var tableBot = myBot;
        if (!front) {
          /* Cutting bed top surface */
          polygon(
            [proj([mx0, tableTop], 0), proj([mx1, tableTop], 0), proj([mx1, tableTop], 1), proj([mx0, tableTop], 1)],
            "#1c3340", "#45687a", 1.1
          );
          /* Rear upright columns (z=1) */
          polygon(
            [proj([mx0, tableTop], 1), proj([mx0 + colW, tableTop], 1), proj([mx0 + colW, myTop], 1), proj([mx0, myTop], 1)],
            "#223a48", "#4f7386", 1
          );
          polygon(
            [proj([mx1 - colW, tableTop], 1), proj([mx1, tableTop], 1), proj([mx1, myTop], 1), proj([mx1 - colW, myTop], 1)],
            "#223a48", "#4f7386", 1
          );
          /* Rear upper crossbeam */
          polygon(
            [proj([mx0, myTop - colW], 1), proj([mx1, myTop - colW], 1), proj([mx1, myTop], 1), proj([mx0, myTop], 1)],
            "#274252", "#587e92", 1
          );
          /* Side rails joining front & rear gantry top */
          segLine(proj([mx0 + colW * 0.5, myTop - colW * 0.5], 0), proj([mx0 + colW * 0.5, myTop - colW * 0.5], 1), "#54798c", 2);
          segLine(proj([mx1 - colW * 0.5, myTop - colW * 0.5], 0), proj([mx1 - colW * 0.5, myTop - colW * 0.5], 1), "#54798c", 2);
        }
        /* Front table fascia */
        polygon(
          [proj([mx0, tableBot], 0), proj([mx1, tableBot], 0), proj([mx1, tableTop], 0), proj([mx0, tableTop], 0)],
          "#243b49", "#55798b", 1.1
        );
        /* Millimeter ruler ticks on table edge */
        var ticks = [0, 0.25, 0.5, 0.75, 1];
        ctx.fillStyle = "#95b7c8";
        ctx.font = "10px Consolas, monospace";
        ticks.forEach(function (t) {
          var rx = b.x_min + b.width * t;
          var tp = proj([rx, tableTop], 0);
          var bp = proj([rx, tableTop - (tableTop - tableBot) * 0.42], 0);
          segLine(tp, bp, "#7ea3b6", 1);
          if (w >= 460 || t === 0 || t === 1) {
            var lbl = Math.round(rx) + (t === 1 ? " mm" : "");
            ctx.fillText(lbl, tp[0] - (t === 1 ? 26 : 8), bp[1] + 10);
          }
        });
      }

      /* 3. Schematic EPS block with procedural bead texture */
      if (stock) {
        var a = [x0, y0], c = [x1, y0], e = [x1, y1], f = [x0, y1];
        if (!front) {
          /* Bottom base shadow */
          polygon([proj(a, 0), proj(c, 0), proj(c, 1), proj(a, 1)], "rgba(35,64,78,0.6)", "#517284", 1);
          /* Right or left visible side face depending on angle */
          if (dx >= 0) {
            polygon([proj(c, 0), proj(e, 0), proj(e, 1), proj(c, 1)], "rgba(210,228,236,0.22)", "#7e9fae", 1);
          } else {
            polygon([proj(a, 0), proj(f, 0), proj(f, 1), proj(a, 1)], "rgba(210,228,236,0.22)", "#7e9fae", 1);
          }
          /* Top face with EPS bead tint */
          polygon([proj(f, 0), proj(e, 0), proj(e, 1), proj(f, 1)], "rgba(232,243,248,0.3)", "#8aaab9", 1);
        }
        /* Front face with EPS cellular bead texture */
        polygon([a, c, e, f].map(function (p) { return proj(p, 0); }), epsBlockPat, "#9ab8c7", 1.2);
      }

      /* 4. Demonstrable nominal XY cut regions (progressive reveal behind wire X) */
      var offsets = dual ? [0, offset] : [0];
      if (showRegions && dist > 0) {
        var clipXScreen = proj([pos.p[0], b.y_min], 0)[0];
        var leftEdgeScreen = proj([b.x_min, b.y_min], 0)[0] - 2;
        ctx.save();
        ctx.beginPath();
        ctx.rect(leftEdgeScreen, 0, Math.max(0, clipXScreen - leftEdgeScreen), h);
        ctx.clip();
        offsets.forEach(function (o, k) {
          var lowPts = regions.lower_region_xy.map(function (pt) { return proj(pt, 0, o); });
          var upPts = regions.upper_region_xy.map(function (pt) { return proj(pt, 0, o); });
          polygon(
            lowPts,
            k ? "rgba(244,234,224,0.45)" : epsLowerPat,
            k ? "rgba(255,152,102,0.55)" : "rgba(182,226,238,0.85)",
            1.1
          );
          polygon(
            upPts,
            k ? "rgba(160,126,110,0.22)" : "rgba(96,138,162,0.34)",
            "rgba(116,158,180,0.42)",
            0.9
          );
        });
        ctx.restore();
      }

      /* 5. Nominal remaining path + traversed cut surfaces + dual hotwires */
      var wireAnchors = [];
      offsets.forEach(function (o, k) {
        var surfFill = k ? "rgba(255,148,96,0.28)" : "rgba(78,224,196,0.34)";
        var cutStroke = k ? "#ff9c6e" : "#56e6c8";
        var wireCore = k ? "#ff8a5b" : "#ffd166";
        var wireGlow = k ? "rgba(255,94,58,0.5)" : "rgba(255,144,44,0.55)";

        if (showPath) {
          ctx.beginPath();
          var start = proj(seg[0].start, 0, o);
          ctx.moveTo(start[0], start[1]);
          for (var si = 0; si < seg.length; si++) {
            var q0 = proj(seg[si].end, 0, o);
            ctx.lineTo(q0[0], q0[1]);
          }
          ctx.strokeStyle = k ? "rgba(235,176,144,0.42)" : "rgba(164,199,214,0.52)";
          ctx.setLineDash([5, 5]);
          ctx.lineWidth = 1.2;
          ctx.stroke();
          ctx.setLineDash([]);
        }

        /* Swept cut surface ribbons + traversed front contour */
        for (var i = 0; i <= pos.i; i++) {
          var s = seg[i];
          var end = i === pos.i ? pos.p : s.end;
          if (!front) {
            polygon(
              [proj(s.start, 0, o), proj(end, 0, o), proj(end, 1, o), proj(s.start, 1, o)],
              surfFill,
              "rgba(255,255,255,0.08)",
              0.5
            );
          }
          segLine(proj(s.start, 0, o), proj(end, 0, o), cutStroke, 2.3);
        }

        /* Hotwire filament (front-to-back in iso, glowing point in front XY) */
        var p = proj(pos.p, 0, o);
        var q = proj(pos.p, 1, o);
        wireAnchors.push({ p: p, q: q, k: k, o: o });

        if (!front) {
          segLine(p, q, wireGlow, 8);
          segLine(p, q, wireCore, 3);
          /* Wire bow holders at front and rear ends */
          [p, q].forEach(function (pt) {
            ctx.fillStyle = "#c9dae3";
            ctx.strokeStyle = "#203642";
            ctx.lineWidth = 1;
            ctx.fillRect(pt[0] - 4, pt[1] - 6, 8, 5);
            ctx.strokeRect(pt[0] - 4, pt[1] - 6, 8, 5);
          });
        }
        /* Glowing hotwire tip indicator */
        ctx.beginPath();
        ctx.arc(p[0], p[1], 7.5, 0, Math.PI * 2);
        ctx.fillStyle = wireGlow;
        ctx.fill();
        ctx.beginPath();
        ctx.arc(p[0], p[1], 4.2, 0, Math.PI * 2);
        ctx.fillStyle = wireCore;
        ctx.fill();
        ctx.strokeStyle = "#fff8dc";
        ctx.lineWidth = 1.1;
        ctx.stroke();
      });

      /* 6. Schematic SCARA machine — front gantry columns, bridge & synchronized moving carriages */
      if (showMachine) {
        var topY = y0 - framePadBot * 0.08;
        /* Front left & right columns */
        polygon(
          [proj([mx0, topY], 0), proj([mx0 + colW, topY], 0), proj([mx0 + colW, myTop], 0), proj([mx0, myTop], 0)],
          "#2d4959", "#6d92a5", 1.1
        );
        polygon(
          [proj([mx1 - colW, topY], 0), proj([mx1, topY], 0), proj([mx1, myTop], 0), proj([mx1 - colW, myTop], 0)],
          "#2d4959", "#6d92a5", 1.1
        );
        /* Front upper bridge beam with subtle Iso Nunes red accent stripe */
        polygon(
          [proj([mx0, myTop - colW * 1.15], 0), proj([mx1, myTop - colW * 1.15], 0), proj([mx1, myTop], 0), proj([mx0, myTop], 0)],
          "#325061", "#789eb2", 1.1
        );
        segLine(
          proj([mx0 + colW * 1.2, myTop - colW * 0.55], 0),
          proj([mx1 - colW * 1.2, myTop - colW * 0.55], 0),
          "#d63638",
          2.2
        );

        /* Moving X-carriage on upper bridge & vertical SCARA arm tracking live X/Y */
        var carX = pos.p[0];
        var carTop = proj([carX, myTop - colW * 0.55], 0);
        var highestWireY = pos.p[1] + (dual ? offset : 0);
        var carWireTop = proj([carX, highestWireY], 0);
        segLine(carTop, carWireTop, "rgba(180,210,226,0.6)", 2, [3, 3]);
        ctx.fillStyle = "#e3eff5";
        ctx.strokeStyle = "#18303d";
        ctx.lineWidth = 1.2;
        ctx.fillRect(carTop[0] - 8, carTop[1] - 5, 16, 10);
        ctx.strokeRect(carTop[0] - 8, carTop[1] - 5, 16, 10);

        /* Side Y-guide sliders on left/right front columns */
        wireAnchors.forEach(function (wa) {
          var wy = pos.p[1] + wa.o;
          var leftSlide = proj([mx0 + colW * 0.5, wy], 0);
          var rightSlide = proj([mx1 - colW * 0.5, wy], 0);
          ctx.fillStyle = wa.k ? "#ff8a5b" : "#ffd166";
          ctx.fillRect(leftSlide[0] - 4, leftSlide[1] - 3, 8, 6);
          ctx.fillRect(rightSlide[0] - 4, rightSlide[1] - 3, 8, 6);
        });
      }

      /* 7. Clear callout pills for Wire 1 and schematic Wire 2 */
      if (wireAnchors.length) {
        var w1 = wireAnchors[0];
        var lbl1 = w < 420 ? "F1" : "Fio 1";
        pillLabel(lbl1, w1.p[0] + 10, w1.p[1] + 6, "rgba(25,38,48,0.92)", "#ffe28a", "#ffd166");
        if (wireAnchors.length > 1) {
          var w2 = wireAnchors[1];
          var lbl2 = w < 420 ? "F2 (esq.)" : "Fio 2 (esq.)";
          pillLabel(lbl2, w2.p[0] + 10, w2.p[1] - 25, "rgba(38,24,22,0.92)", "#ffc0a4", "#ff8a5b");
        }
      }

      /* 8. Bottom status strip inside canvas */
      ctx.fillStyle = "rgba(10,22,30,0.72)";
      ctx.fillRect(0, h - 24, w, 24);
      ctx.fillStyle = "#c8dde8";
      ctx.font = "11px system-ui, -apple-system, Segoe UI, Arial, sans-serif";
      var summary = w < 440
        ? ("XY nominal · " + (dual ? "2 fios (esq.)" : "1 fio") + " · " + (front ? "frontal" : "persp."))
        : ("XY nominal · " +
          (dual ? "2 fios (esquemático)" : "1 fio") +
          (showRegions ? " · regiões nominais" : "") +
          " · " + (front ? "vista frontal XY" : "perspectiva"));
      ctx.fillText(summary, 12, h - 8);

      /* Update live DOM telemetry */
      var pct = Math.round((dist / total) * 100);
      $("cut-percent").textContent = pct + "%";
      $("cut-seek").value = Math.round((dist / total) * 1000);
      $("cut-x").textContent = fmt(pos.p[0]) + " mm";
      $("cut-y").textContent = fmt(pos.p[1]) + " mm";
      $("cut-block").textContent = "N" + seg[pos.i].block;
      $("cut-distance").textContent = fmt(dist) + " mm";
      if ($("cut-step-info")) {
        $("cut-step-info").textContent = "Bloco " + (pos.i + 1) + " / " + seg.length;
      }
    }

    function resize() {
      var rect = canvas.getBoundingClientRect();
      var dpr = Math.min(2, window.devicePixelRatio || 1);
      w = rect.width;
      h = rect.height;
      canvas.width = Math.max(1, Math.round(w * dpr));
      canvas.height = Math.max(1, Math.round(h * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      paint();
    }

    function stop() {
      playing = false;
      cancelAnimationFrame(raf);
      last = 0;
      $("cut-play").textContent = "Reproduzir";
      $("cut-play").setAttribute("aria-pressed", "false");
    }

    function togglePlay() {
      if (playing) { stop(); return; }
      if (dist >= total) dist = 0;
      playing = true;
      $("cut-play").textContent = "Pausar";
      $("cut-play").setAttribute("aria-pressed", "true");
      raf = requestAnimationFrame(tick);
    }

    function tick(t) {
      if (!playing) return;
      if (last) {
        dist = Math.min(total, dist + Math.min(0.1, (t - last) / 1000) * (total / 16) * Number($("cut-speed").value));
      }
      last = t;
      paint();
      if (dist >= total) stop();
      else raf = requestAnimationFrame(tick);
    }

    function seek(d) {
      stop();
      dist = Math.max(0, Math.min(total, d));
      paint();
    }

    function stepNext() {
      var i = locate(dist).i;
      if (dist >= seg[i].end_distance_mm - 1e-7) i = Math.min(i + 1, seg.length - 1);
      seek(seg[i].end_distance_mm);
    }

    function stepPrev() {
      var i = locate(dist).i;
      seek(i ? seg[i - 1].end_distance_mm : 0);
    }

    function toggleFullscreen() {
      if (!$("cut-stage").requestFullscreen) return;
      if (document.fullscreenElement) document.exitFullscreen();
      else $("cut-stage").requestFullscreen().catch(function () {});
    }

    $("cut-play").addEventListener("click", togglePlay);
    $("cut-seek").addEventListener("input", function () { seek(total * Number(this.value) / 1000); });
    $("cut-reset").addEventListener("click", function () { seek(0); });
    $("cut-next").addEventListener("click", stepNext);
    $("cut-prev").addEventListener("click", stepPrev);

    ["cut-view", "cut-angle", "cut-zoom", "cut-dual", "cut-stock", "cut-regions", "cut-machine", "cut-path"].forEach(function (id) {
      var el = $(id);
      if (!el) return;
      el.addEventListener("input", paint);
      el.addEventListener("change", paint);
    });

    document.addEventListener("keydown", function (ev) {
      var tag = ev.target && ev.target.tagName;
      if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;
      if (ev.code === "Space") { ev.preventDefault(); togglePlay(); }
      else if (ev.code === "ArrowRight") { ev.preventDefault(); stepNext(); }
      else if (ev.code === "ArrowLeft") { ev.preventDefault(); stepPrev(); }
      else if (ev.key === "r" || ev.key === "R") { seek(0); }
      else if (ev.key === "f" || ev.key === "F") { toggleFullscreen(); }
    });

    document.addEventListener("visibilitychange", function () { if (document.hidden) stop(); });
    if ($("cut-stage").requestFullscreen) {
      $("cut-full").hidden = false;
      $("cut-full").addEventListener("click", toggleFullscreen);
    }
    document.addEventListener("fullscreenchange", resize);
    window.addEventListener("resize", resize);

    $("cut-fallback").hidden = true;
    canvas.hidden = false;
    $("cut-controls").hidden = false;
    if ($("cut-legend")) $("cut-legend").hidden = false;
    $("cut-error").hidden = true;
    resize();
  }

  fetch(root.dataset.source, { credentials: "same-origin", cache: "no-store" })
    .then(function (r) { if (!r.ok) throw Error("HTTP " + r.status); return r.json(); })
    .then(init)
    .catch(function () {
      $("cut-error").textContent = "Não foi possível carregar a animação desta revisão. A prévia estática permanece disponível.";
    });
}());
