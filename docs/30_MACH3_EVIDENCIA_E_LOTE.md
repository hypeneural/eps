# Mach3: recuperar evidência antes de solicitar dados
## Observado no backup original
CNC_V.xml: DwellinMilli=0, SoftLimit=0, INIT=G80, M30SpinOff=1, NoSpindle=1, M0/M1/M2 Max=100, Min=-100. Estes valores de configuração não são curso físico confirmado. Macros M3/M5 chamam DoSpinCW/DoSpinStop. isopor.pst contém F600, S300 e G4 P3. São valores documentais, não máximos autorizados. O TAP original da TP40 Base lisa (1063 bytes) existe; não corresponde byte a byte à trajetória continuous_clean recém-planejada. Quatro outras variantes não têm TAP histórico exato.
## Comandos
```powershell
python scripts/recover_cnc_v_evidence.py "private_evidence/MACROS_CNC_V.zip" --output outputs/cnc_v_evidence.json
python scripts/prepare_private_handoff.py --output outputs/handoff_novo
python scripts/prepare_mach3_batch.py --handoff outputs/handoff_novo --list
```
A recuperação deve acontecer antes de perguntar por dados. Não solicitar novamente valores documentais já encontrados, apenas confirmar vigência e lacunas físicas. Não confundir campo M0Max/M1Max com capacidade, sobretudo com SoftLimit=0. Consulte https://www.machsupport.com/help-learning/product-manuals/ e https://www.machsupport.com/help-learning/f-a-q/.
## Lote
O --list retorna hashes de projeto e trajetória. O responsável revisa cada modelo e registra em approvals.json um objeto indexado pelo ID retornado, com trial_authorized:true, path_sha256 e project_sha256 correspondentes. Não preencher autorização automaticamente. A configuração local e o contrato já revisados são compartilhados pelo lote:
```powershell
python scripts/prepare_mach3_batch.py --handoff outputs/handoff_novo --profile local_scara_snapshot.yaml --contract local_trial_contract.json --approvals approvals.json --output outputs/lote_tap
```
Gera um TAP individual por modelo autorizado, relatório por item e código de saída não zero se algum item falhar; não modifica flags ou publica. Não confundir saída de teste com produção. Reutilizar aprovação por hashes e download individual existentes após homologação; nunca renomear histórico para uma variante diferente. Não há necessidade de rodar cinco comandos.
## Entrega
O portal já possui botão TAP e arquivos individuais quando production_released e tap_approved passam os gates. Conferir arquivo real por SHA-256 e HTTPS depois da publicação. Não exibir botão verde para arquivo inexistente. A biblioteca histórica privada pode ser importada separadamente; conservar os bytes originais. Não publicar XML, PST ou macros.
