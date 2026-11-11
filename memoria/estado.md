# Estado do projeto
## Sprints 1 e 2 — completas
- Coletor ML catálogo, veredito, anti-golpe; bot /adicionar /lista /remover /apelido; webhook Vercel
- GitHub: https://github.com/luthhop/lowpoint; 3 watches ativos (PS5, LG 27", AOC 27")
- LG 32" (product 1, watch 1) INATIVO desde 09/11 07:59: não é coletado, histórico parado em 6 dias
## Sprint 3 — em andamento
- Pós-pico: ≤3% SEGURA (template C), 3–5% MONITORANDO, ≥5% + menor histórico = PODE IR
- Backtest real 10/11: 81 vereditos, 0 mudanças, 0 picos (histórico <14d não exercita o fix)
- PROBLEMA agendador: cron GitHub de hora em hora disparou só 3–5x/dia (intervalo mediano 7h, 03–10/11)
- Solução local (sem push): /api/tick na Vercel dispara workflow_dispatch + aviso Telegram se coleta >90 min
- Pendente Lucas: token fine-grained, env vars na Vercel, cron externo 15 min, `alembic upgrade head` (system_state)
- Coleta: timeout (5s,15s), retry 429/5xx/rede (3 tentativas), log de chamadas por execução
- 247 testes Python + 5 frontend (10/11)
## Design e landing
- Landing publicada: https://lowpoint-web.vercel.app; projeto lowpoint-web, raiz frontend
- Lucas quer animações com mais impacto — ritmo etiqueta → histórico → SEGURA → desconto real → alerta
## Próximo
- Ligar o tick antes de 23/11; decidir sobre reativar LG 32"
- Animações da landing; dashboard pós-Black Friday
