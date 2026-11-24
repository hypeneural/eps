# Backup do PC Mach3 / Perfil EPS

Data: 2026-05-29

Nao atualizar, reinstalar, formatar ou substituir o PC da maquina antes de backup completo. O PC antigo faz parte do sistema de producao.

## Itens a copiar

| Item | Caminho comum | Status |
| --- | --- | --- |
| Pasta Mach3 completa | `C:\Mach3\` | pendente |
| Perfil EPS XML | `C:\Mach3\*.xml` | pendente |
| Licenca Mach3 | `C:\Mach3\Mach1Lic.dat` | pendente |
| Macros do perfil | `C:\Mach3\macros\` | pendente |
| Screensets | `C:\Mach3\*.set` | pendente |
| Plugins | `C:\Mach3\PlugIns\` | pendente |
| Brains | `C:\Mach3\Brains\` | pendente |
| LazyCam | pasta instalada do LazyCam | pendente |
| Pasta Scara/EPS local | desktop/disco do PC | pendente |
| Atalhos da area de trabalho | desktop do operador | pendente |
| G-codes reais | `.tap`, `.nc`, `.txt` | pendente |
| DXF/DWG reais | arquivos usados hoje | pendente |

## Registro minimo

```text
data_backup:
responsavel:
pc_nome:
windows:
mach3_versao:
perfil_usado:
lazycam_versao:
midia_destino:
hash_ou_observacao:
```

## Regra operacional

- Fazer copia simples dos arquivos antes de qualquer teste.
- Quando possivel, criar imagem completa do HD.
- Validar se o Mach3 abre com o perfil EPS no PC original antes e depois da copia.
- Nao alterar configuracoes do Mach3 sem registrar em `docs/DECISOES_TECNICAS.md`.
