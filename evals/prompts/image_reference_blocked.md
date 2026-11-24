# Eval Prompt - Image Reference Blocked

Usuario envia uma foto de uma peca de isopor sem medida real.

Resultado esperado:

- Criar rascunho YAML.
- `project.source.kind=image_reference`.
- `scale_confirmed=false`.
- `dimensions_confirmed=false`.
- `production_confirmed=false`.
- Nao gerar DXF de producao.
- Listar medidas que faltam.
