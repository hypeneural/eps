# Biblioteca de lajes EPS — pesquisa e primeiras referências
Pesquisa 24/11/2026. Não copiar fotografias com marca d'água, logotipos, arquivos CAD de terceiros ou certificados sem licença/autorização. Render próprio baseado em geometria nominal explícita.
## Fontes
- Isopack moldada: https://www.isopack.com.br/produto/capa-de-laje-em-eps-moldada/ — 1250 x 330 x 70 mm, encaixe publicado 25 x 15 mm, densidade publicada 11–13 kg/m³. Relevo moldado não reproduzível por uma extrusão XY simples.
- Isopack padrão: https://www.isopack.com.br/produto/capa-de-laje-em-eps-modelo-padrao/ — 1000 mm, 330–400 mm, H70–250 mm, encaixe 27x15 personalizável. Combinações do nosso catálogo são nominais, não SKUs homologados.
- Styroville: https://styroville.com.br/produto/capa-de-laje-tavela-em-eps/ — diferencia moldada de recortada, com recortada 1000 x 330 x 70 mm.
- Isoplast: https://isoplast.ind.br/16/produto/lajota-eps-unidirecional-e-bidirecional — tabela dimensional e chanfros hxb; não confundir chanfro com rebaixo retangular.
- Isorecort: https://www.isorecort.com.br/lajotas/ — 1000 mm, larguras 330/400/440, unidirecional, universal, bidirecional com abas.
- Kingspan: https://kingspan-isoeste.com.br/solucoes-kingspan/lajota-eps-padrao/ — 330/400 mm, 1000/2000 mm e biblioteca BIM: https://kingspan-isoeste.com.br/tudo-para-voce/biblioteca/biblioteca-bim/ . Não confirmado arquivo CAD específico de tavela.
- 3D Warehouse: https://embed-3dwarehouse-classic.sketchup.com/model/ba76a5fd-bfc5-4668-b16a-97e417cc3d92/Laje-Treli%C3%A7a-e-Painel-Treli%C3%A7ado — referência de montagem, não CAM.
- CadQuery: https://cadquery.readthedocs.io/en/latest/importexport.html — STEP/DXF; avaliar apenas se o pipeline existente precisar de CAD B-rep.
- CAM: https://github.com/JHU-DBF/HotWire_CNC_gcode_generator e https://github.com/Shkolik/Foamcut — investigar algoritmos, licença e cinemática; não usar G-code de 4/5 eixos no CNC_V.
## Implementação
`python scripts/prepare_slab_reference.py --list` e `python scripts/prepare_slab_reference.py capa-laje-h7-1250 --output outputs/capa_h7_1250_review`.
Quatro referências iniciais; polígonos matemáticos com rebaixos inferiores simétricos assumidos (primeiro número interpretado como largura, segundo como altura). Sem chanfro ou estampa moldada. Verificar desenho cotado real e vigota. Os arquivos STL mm, GLB m, PNG de seção, preview CPU, hashes e EPS_REVISAO.zip entram no portal com registro explícito de publicação e status draft. Não contém TAP ou DXF.
## Próximas etapas
Validar H7/H8/H12 e dimensões dos encaixes com desenho e amostra da fábrica. Separar largura total/útil, altura, comprimento de extrusão, chanfros/rebaixos. Procurar correspondências nos arquivos históricos H10/H11/H12/H15 e bidirecionais, sem assumir dimensões pelo nome. Criar planejador CAM de seção constante independente da geometria; comprimento de extrusão não é deslocamento XY. Bidirecional com abas nas duas direções pode exigir cortes adicionais/rotação ou processo diferente. Relevo localizado exige moldagem ou outra operação, não textura disfarçada. Reusar prepare_mach3_trial.py para teste privado com contrato real; somente após homologação publicar TAP direto pelo fluxo existente. Não certificar desempenho estrutural com base em catálogos concorrentes; confirmar especificação do projeto de laje e normas aplicáveis com responsável técnico.
