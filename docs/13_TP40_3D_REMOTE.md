# TP40 3D e entrega remota (Antigravity)
## Fonte e limites
- SKS TP40/980, catalogo p.21: 196/36/32/98 mm (passo/altura/crista/vale), largura util 980, total chapa 1032. Microperfil 2 mm, cota 48 mm: nao modelado.
- Isoeste TP40/1020, ficha p.2: 255/40/35/143 mm, largura util 1020, total 1074. Microdobras e bordas nao modeladas.
- Inovaiso https://inovaiso.com.br/produto/telha-eps-trapezio-tp40-980/ informa placas 1000/2000 mm, espessuras comerciais 20/30/50 mm, EPS T1F 10 kg/m3 para aquele produto.
- As fotos mostram face plana e interface trapezoidal com pequenas dobras. Nao ha escala. Fase, bordas, raios, espessura real, folga e densidade precisam de medicao.
## Uso no Antigravity 2.35.0
Abra a raiz EPS e rode os comandos do README no terminal Python. Nenhuma API do Antigravity e necessaria. Consulte AGENTS.md e mantenha G-code desabilitado.
## Saidas
20 EPS STL, 21 contraforma STL, 22 chapa STL: mm. 23 conjunto GLB, 24 EPS GLB: metros. Material visual EPS sintetico e metal PBR. 25 textura PNG, 26 render EPS, 27 conjunto explodido: render CPU ilustrativo, nao fotometrico.
03 DXF R12 apenas quando permitido, somente percurso XY. Nunca envie STL/GLB ao LazyCam. 12 ZIP: revisar status/manifest e hashes; draft e teste nao sao producao.
## Homologacao
Medir face interna da chapa, passo em varias ondas, fase, bordas, dobras, folga e espessura; aprovar encaixe em corpo de prova. Preencher perfil SCARA, calibrar fio/velocidade, validar LazyCam 1:1, origem, leads, sentido, dry-run sem calor e corte teste. Complemento nominal antes da perda termica.
Bibliotecas: https://github.com/mikedh/trimesh, https://github.com/shapely/shapely, https://github.com/skogler/mapbox_earcut_python e Pillow. Sem copiar codigo de maquinas ou alterar Mach3.
