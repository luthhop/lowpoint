# Estado do projeto
## Sprint 1 — completa
- Schema, coletor, veredito, best_offer, proteção anti-golpe, GitHub Actions (coleta horária)
- Repositório público: https://github.com/luthhop/lowpoint
- 2 produtos reais registrados (MLB24061510 monitor LG, MLB57081243 PS5)
## Sprint 2 — em andamento
- Bot Telegram: formatter, security, notify, webhook implementados
- Alertas integrados no coletor (após cada coleta, via API Telegram)
- Webhook Vercel (api/webhook.py) para comandos /adicionar /lista /remover
- Anti-spam: alerta do mesmo tipo só se preço cair abaixo do último enviado
- Campo nickname na Watch (migration a1b2c3d4e5f6)
- 107 testes passando (2 novos para isolamento de alertas)
- Scripts utilitários: telegram_whoami.py, set_webhook.py, update_chat_id.py
- Dependências da Vercel verificadas (psycopg2-binary, sqlalchemy, dotenv OK)
- **Pendente:** deploy Vercel, registrar webhook no Telegram, secret TELEGRAM_BOT_TOKEN no Actions, migração no Neon, testar fluxo completo
## Plano até Black Friday
- Semana 3 (até 22/11): veredito real/maquiado nos alertas, bot rodando 24/7
- Pós-BF: telas no Paper, dashboard, landing page, análise dos dados
