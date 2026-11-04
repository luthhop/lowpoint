# Estado do projeto
## Sprint 1 — completa
- Schema, coletor, veredito, best_offer, proteção anti-golpe, GitHub Actions (coleta horária)
- Repositório público: https://github.com/luthhop/lowpoint
- 2 produtos reais registrados (MLB24061510 monitor LG, MLB57081243 PS5)
## Sprint 2 — completa
- Bot Telegram funcionando: /adicionar /lista /remover /apelido
- Alertas com veredito integrados no coletor (após cada coleta)
- Webhook Vercel (api/webhook.py) deployado e respondendo
## Sprint 3 — em andamento
- Tudo de antes +
- Fix: filtro anti-golpe com historical_median (< 3 ofertas usa mediana do histórico)
- Coleta anômala: se ofertas caem a < 30% do normal, grava dados mas suprime alertas
- Aviso "poucos vendedores" no footer quando < 3 ofertas
- recalc_price_history.py atualizado com historical_median cronológico
- 162 testes passando
## Pendências
- Remover alerta espúrio id=1 (R$ 1.500 do PS5, gerado em teste local)
- Remover "Fone Teste" (watch id=3, já inativo)
- Deploy do fix (push + redeploy Vercel)
## Plano até Black Friday
- Semana 3 (até 22/11): veredito refinado, bot 24/7
- Pós-BF: telas no Paper, dashboard, landing page
