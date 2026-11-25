# V7 — interface compacta e critério de conclusão industrial
Base 36a10fa: V6 5/5 checks verdes, 9 páginas, mas zero TAP industrial. Os checks de interface e fixture sintética não certificam entrega industrial.
## Interface
Cabeçalho sticky nas páginas, logo original, ícone WhatsApp de 44px persistente no topo da apresentação, links acessíveis sem JavaScript, cartões compactos, ZIP secundário. A página pública mantém somente dados de apresentação e OG; sem downloads de máquina. Status único no cartão quando TAP não existe: TAP pendente · não usar para corte. Não ocultar uma pendência real. Testar âncoras, foco e scroll em sete resoluções e sem JS.
## Entrega real
Execute o lote existente com os nove projetos e contrato revisado; não apenas --list. A tarefa industrial exige arquivos reais e aprovação da revisão correspondente, não uma fixture. A verificação independente de entrega agora é:
```powershell
python scripts/check_mach3_delivery.py --site outputs/site_v7_catalog9
python scripts/check_mach3_delivery.py --site outputs/site_v7_catalog9 --https
```
Código de saída 1 se qualquer um dos nove estiver sem TAP aprovado, sem bytes, sem hash ou sem link direto. Não declarar entrega 9/9 com zero arquivos; publicar visual mesmo se a entrega industrial estiver pendente. O verificador não homologa fisicamente, não modifica arquivo, nem gera aprovação.
## Evidência
Medidas nominais das peças já estão no catálogo e planejadores. O backup histórico demonstra sintaxe e parâmetros utilizados em outros trabalhos, não a capacidade atual nem adequação de novas trajetórias. Consultar https://www.machsupport.com/help-learning/product-manuals/ e https://www.machsupport.com/help-learning/f-a-q/. Confirmar presencialmente somente as lacunas reais da ficha do relatório 31; não inferir curso físico a partir de catálogos ou limites desativados. Não trocar TAP original por variante nova. Revisões alteradas devem ter nova identidade.
## Deploy
Gerar snapshot novo, validar UI, dry-run, FTPS incremental e auditoria HTTPS. Não publicar fixtures, candidatos experimentais nem credenciais. Publicar apenas programas aprovados com hash e autorização. Se entrega parcial, declarar contagem real e os motivos por peça. Não usar --initialize no site existente.
