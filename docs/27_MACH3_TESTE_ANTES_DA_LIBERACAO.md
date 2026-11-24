# Mach3 — geração de teste antes da liberação comercial
## Decisão
A exigência anterior de production_released para gerar qualquer TAP de teste criava uma dependência circular: testar precisava de aprovação de produção que dependia do teste. A partir desta alteração, há uma rota separada de candidato local. Nenhuma flag de produção é alterada pelo teste. Não equivale a homologação física nem à publicação.
## Rotas
- Sem dados reais: auditoria dos TAP históricos, simulação offline, geração de geometria nominal e relatório de trajetória; usar scripts/import_historical_taps.py, scripts/simulate_tap.py e scripts/inspect_ordered_path.py. Identificar hipóteses e não reutilizar TAP de família diferente.
- Teste presencial: projeto YAML validated_geometry (produção não confirmada), snapshot local da SCARA com valores medidos, contrato local revisado com finalidade local_supervised_trial e operator_trial_authorized true. O campo contract segue KEYS/FLAGS de mach3_tap.py; valores de limites, origem, avanço, saída e temporização devem ser confirmados para o teste. Não exige profile_locked=true ou safety.production_allowed=true. Não editar perfil versionado para fabricar evidência.
- Produção: fluxo anterior, perfil travado, gates, simulação e aprovação humana por hashes. Portal sem login não é local de distribuição de programas de teste.
## Comandos
```powershell
python scripts/import_historical_taps.py "private_evidence/isonunes Projetos.zip" --output outputs/historical_review
python scripts/prepare_mach3_trial.py --help
python scripts/prepare_mach3_trial.py <projeto.yaml> --profile <snapshot-local.yaml> --contract <contrato-teste-local.json> --output outputs/teste_privado_r01
```
O contrato local tem a forma {purpose: local_supervised_trial, operator_trial_authorized: true, contract: {...}} (JSON válido com chaves entre aspas). O hash machine_profile_sha256 vincula o snapshot exato; calcular com sha(canonical(profile)) do módulo mach3_tap. Não preencher confirmações automaticamente. O perfil usado por build_job permanece o perfil do projeto versionado; o snapshot local é usado para verificar parâmetros e limites do pós-processador. Se o projeto não passar validação geométrica, corrigir a causa, não contornar.
## Entregáveis
TESTE-NAO-HOMOLOGADO.tap, simulacao.png, relatorio.json, LEIA-ME.txt. Sem publicação e sem alterar registro local de produção. O arquivo TAP é texto ASCII; extensão .tap preferida porque o diálogo observado da CNC_V filtra *.tap. Relatório TXT não é programa de corte. Manual oficial: https://www.machsupport.com/ftp/Docs/Mach3Mill_1.84.pdf (6.4).
## Limites desta etapa
Só uma trajetória linear contínua ordenada. Arcos e contornos de referência não são convertidos automaticamente. As cinco peças reais precisam de correspondência individual entre catálogo, trajetória e evidência. TP40 base lisa tem retornos específicos; o planejador dedicado continua necessário. Não declarar corte real validado por simulação.
