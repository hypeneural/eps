---
name: eps-render-quality
description: Renderiza e revisa GLB/STL, textura de pérolas EPS e chapa de referência com Blender Cycles ou preview CPU; use para melhorar imagens ou vistas.
---

# Procedimento
Leia docs/14_ANTIGRAVITY_LOCAL.md e docs/17_HOMOLOGACAO_LOCAL_RELATORIO.md. Reutilize GLB e renders verificados do mesmo pacote. Se faltarem vistas, prepare_tp40.py --blender auto gera seis vistas integradas ao ZIP; render_quality.py --help permite render isolado fora do pacote já verificado. Vistas: perspective, section_front, microgroove_detail, assembly, exploded, texture_closeup. Use Blender 4.2+ com GPU quando disponível; CPU é fallback. Nunca substitua CAD por imagem gerada por IA. Inspecione enquadramento, topo, microdobras, textura e chapa; contraste e cyclorama são questões visuais. Não sobrescreva arquivo com hash; se precisar modificar pacote, regenere-o em nova pasta. Registre backend efetivo, vistas, inspeção e limitações.
