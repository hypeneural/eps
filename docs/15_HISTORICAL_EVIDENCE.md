# Evidencias historicas SCARA: revisao local
- Manual do fabricante indica DXF R12 em mm, importacao Foam, conferencia de origem, continuidade, direcao e sobreposicao. Preservar LazyCam e Mach3.
- A coleta pode conter arquivos de instalacao diferente do executavel ativo; conferir caminho e perfil antes de homologar.
- Configuracao CAM armazenada nao e necessariamente o modo modal dos TAPs. S/F historicos nao sao parametros aprovados. Nao inferir area fisica por bbox de desenho.
- O DXF historico pode incluir linhas de entrada, linhas repetidas, retornos e esquadrejamento. A geometria de produto nao equivale ao caminho completo.
- Para perfil de linhas com topo plano, o recuperador extrai envelope superior dentro de limites explicitamente selecionados, preservando degraus verticais suportados pelo desenho. Nao funciona para ARC, SPLINE, geometria nao planar ou selecao arbitraria de contornos.
- Uso: python scripts/review_historical_roof.py private_evidence/modelo.dxf --left X1 --right X2 --top Y --length L --output outputs/review
- Saida exclusivamente visual: STL, GLB, PNG e JSON com hash da origem; comprimento e chapa ilustrativos. Nenhum DXF ou TAP. A contraforma inclui margem inferior ilustrativa.
- Nao publicar fontes proprietarias nem desenhos reais neste repositorio publico. Testes usam geometria sintetica.
