# Entrega para Antigravity no computador de desenvolvimento

O computador de desenvolvimento e independente do Windows 7 32-bit da fabrica. Instalar Python 3.11/3.13 e opcionalmente Blender apenas no desenvolvimento. Nao conectar/operar a CNC pelo agente.

## Um comando
No PowerShell moderno da raiz do repositorio:
```powershell
powershell -NoProfile -File scripts/prepare_development.ps1
```
Se o ZIP original estiver disponivel, colocar em private_evidence/MACROS_CNC_V.zip (ignorado pelo Git), ou passar -Evidence "C:/caminho/MACROS_CNC_V.zip". Nao e necessario para gerar o perfil de referencia. Nenhuma leitura de disco da fabrica e necessaria. Blender opcional via -Blender "C:/.../blender.exe".

## TP40 referencia normalizada
`python scripts/prepare_tp40.py --output outputs/tp40_review` gera geometria parametricamente, textura EPS, STL mm, GLB m, montagem nominal, PNG tecnico, previews CPU, JSON, SHA256 e ZIP de revisao. Opcional --blender auto e --length/--thickness/--gauge. Dimensoes iniciais: 980 x 67 mm, minimo 31, 5 periodos de 196, rampa 33, crista 98, vale 32, microdobra 48 x 2, area 42560 mm2. Comprimento 1000 mm e bitola .43 mm sao hipoteses visuais. A fase com rampa ascendente inicial e explicita. Referencia nao homologada, sem caminhos de maquina. Se ZIP original estiver disponivel, compara a secao reconstruida com a referencia e falha em divergencia; deduplica por SHA256 sem extrair caminhos arbitrarios. Mudanca de espessura compara historico no baseline.

## Fabrica: fatos e incertezas
Windows 7 Pro SP1 32-bit, PowerShell 2.0, perfil padrao CNC_V, Mach3.sys em execucao e LPT1 detectada. Ha divergencia entre pasta coletada e caminho de executavel ativo; confirmar instalacao e perfil efetivos. Manual: DXF R12 mm, LazyCam Foam, origem, direcao e continuidade. Postprocessador de EPS historico e arquivo TAP sao evidencias, nao comandos autorizados. G21 observado; G90/G91 nao explicitos; valores F/S historicos nao sao limites de operacao. AutoLead desligado no XML coletado: nao presumir entrada/saida automatica. Area util, eixos, fios, kerf, origem, limites, velocidade, aquecimento, encaixe permanecem pendentes. G-code direto bloqueado. Nao atualizar a maquina nem importar configuracao de uma pasta para outra.

## Entrega
Calibracoes existentes sao teste de importacao/dry-run sem calor e supervisao; nao producao. ZIP TP40_REVISAO.zip nunca contem DXF/TAP. Nao confundir com ZIP de calibracao. Inspecionar os PNGs e GLBs reais e abrir o DXF de teste no LazyCam apenas sob responsabilidade do operador. Nao publicar evidencias privadas no GitHub publico. Confirmar medidas/encaixe fisico antes de gerar qualquer percurso TP40 autorizado.
