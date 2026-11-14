# Estado do projeto
## Sprints 1 e 2 — completas
- Coletor ML catálogo, veredito, anti-golpe; bot /adicionar /lista /remover /apelido; webhook Vercel
- GitHub: https://github.com/luthhop/lowpoint; 3 watches ativos (PS5, LG 27", AOC 27")
- LG 32" (product 1, watch 1) INATIVO desde 09/11 07:59: não é coletado, histórico parado em 6 dias
## Sprint 3 — em andamento
- Pós-pico: ≤3% SEGURA (template C), 3–5% MONITORANDO, ≥5% + menor histórico = PODE IR
- Backtest real 10/11: 81 vereditos, 0 mudanças, 0 picos (histórico <14d não exercita o fix)
- Tick ATIVO: cron externo horário às :45 disparando workflow_dispatch (verificado 14/11 no GitHub e no banco)
- /api/tick no main (10/11): dispara workflow_dispatch + aviso Telegram se coleta >90 min
- Aviso falso a cada ~2h (11–13/11): gap 55→25 min p/ batida horária (14/11). Vigiar: scripts/audit_collections.py --hours N
- Coleta: timeout (5s,15s), retry 429/5xx/rede (3 tentativas), log de chamadas por execução
- 507 testes Python (14/11) + 5 frontend; landing App.tsx ainda com linha antiga do PODE IR
## Design e landing
- Landing publicada: https://lowpoint-web.vercel.app; projeto lowpoint-web, raiz frontend
- Lucas quer animações com mais impacto — ritmo etiqueta → histórico → SEGURA → desconto real → alerta
## Próximo
- Ligar o tick antes de 23/11; decidir sobre reativar LG 32"
- Animações da landing; dashboard pós-Black Friday
