---
name: eps-render-quality
description: Renderiza EPS branco com textura de perolas, chapa metalica, GLB, Blender Cycles e preview CPU.
---
# Render
Use GLB da mesma geometria, nunca imagem generativa como CAD. Execute `scripts/render_quality.py --help`. Com Blender 4.2+ use `--blender`, `--input` (GLB EPS ou conjunto) e `--view` (`perspective`, `section_front`, `microgroove_detail`, `assembly`, `exploded`, `texture_closeup`). PNG separado do ZIP de corte verificado. Usa GPU Cycles (OptiX/CUDA) com fallback automatico para CPU. Abra todas as imagens e confira nervuras, microdobras, topo plano, luz, textura de perolas, chapa negativa e escala. Preview CPU e fallback, nao fotorealismo.
