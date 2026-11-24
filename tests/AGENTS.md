# Test Rules

- Todo bug de producao vira teste.
- Testes devem conferir medida, bbox, entidade DXF ou `production_status`; nao basta rodar sem assert.
- Foto sem escala deve estar sempre bloqueada.
- Qualquer `confirmar` usado em producao deve falhar.
- Hotwire sem fio, perda ou feed deve falhar.
- Projeto SCARA/fio quente com campo de fresa, Z, RPM ou profundidade deve falhar no schema.
- G-code direto deve falhar por padrao.
