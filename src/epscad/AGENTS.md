# epscad Code Rules

- Nunca gerar geometria diretamente dentro de exporters.
- Todo exporter recebe `CutJobResult` ou `CutPath[]`, nunca YAML cru.
- Nao colocar regra de maquina dentro de template; regra de maquina fica em validators.
- Templates geram caminhos; validators decidem se o caminho pode virar pacote.
- Mudanca em template exige exemplo YAML e teste com assert numerico.
- G-code direto fica em `postprocessors/` e sempre experimental.
