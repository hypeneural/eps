# Contract - Imagem para Projeto Rascunho

Use quando o usuario enviar foto, print ou croqui.

Saida esperada do Codex:

- Criar ou editar YAML com `project.source.kind=image_reference`.
- Registrar `project.source.image_path` quando existir.
- Definir `project.status=draft`.
- Definir `scale_confirmed=false`.
- Definir `dimensions_confirmed=false`.
- Definir `production_confirmed=false`.
- Gerar apenas preview preliminar quando o codigo existir.
- Listar medidas reais que faltam.

Proibido:

- Gerar DXF de producao.
- Inventar escala.
- Transformar contorno de foto em CutPath final sem confirmacao humana.
