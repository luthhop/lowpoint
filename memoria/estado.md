# Estado do projeto
## Sprint 1 — completa
- Schema Alembic, models SQLAlchemy, verdict.py, best_offer.py (proteção anti-golpe, desempate garantia → oficial)
- PriceSource (ABC + MLCatalogSource + MockSource), collect.py, register.py
- 53 testes passando
- Tokens ML migrados para tabela ml_tokens no banco (SELECT FOR UPDATE)
- Recálculo do price_history aplicado no Neon
- GitHub Actions rodando (coleta horária, ubuntu-24.04, checkout@v5, setup-python@v6)
- Repositório público: https://github.com/luthhop/lowpoint
- README com badge, decisões técnicas, rodando localmente
- 2 produtos reais registrados (MLB24061510 monitor LG, MLB57081243 PS5)
## Sprint atual
- Semana 2 (até 15/11): bot Telegram — /adicionar /lista /remover + alerta de preço-alvo
## Plano até Black Friday
- Semana 3 (até 22/11): veredito real/maquiado nos alertas, bot rodando 24/7
- Pós-BF: telas no Paper, dashboard, landing page, análise dos dados
