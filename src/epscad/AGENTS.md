# epscad Code Rules

- Nunca gerar geometria diretamente dentro de exporters.
- Todo exporter recebe `CutJobResult` ou `CutPath[]`, nunca YAML cru.
- Nao colocar regra de maquina dentro de template; regra de maquina fica em validators.
- Templates geram caminhos; validators decidem se o caminho pode virar pacote.
- Mudanca em template exige exemplo YAML e teste com assert numerico.
- Mach3 TAP usa exporters/mach3_tap.py. Separe render_trial_tap (teste local) de render_tap (produção); ambos compartilham validação de trajetória e leitura modal independente.
