---
name: eps-package-audit
description: Audita manifesto, SHA256, ZIP, DXF R12, unidades, malhas e gates de fabricação; use antes de enviar qualquer pacote ao operador.
---

# Escolha
Pacote de máquina: scripts/verify_package.py --help e scripts/validate_dxf.py --help. Revisão TP40: compare SHA256SUMS.txt, arquivos e TP40_REVISAO.zip, sem DXF/TAP/NC/GCODE. Não aplicar verify_package.py ao ZIP de revisão, cujo contrato é distinto.
# Critérios
Reabra DXF AC1009 por ezdxf; confronte coordenadas, entidades, escala e roundtrip com job quando disponível. Verifique STL fechado e volume, GLB em metros, referências fora do percurso. Confira status, hash e ZIP. Leia docs/02_INVENTARIO_MAQUINA_SCARA.md apenas para limites físicos. Não transformar teste em produção; encaminhe dry-run sem calor supervisionado ao operador. Informe falhas, evidência e ação corretiva; não execute a CNC.
