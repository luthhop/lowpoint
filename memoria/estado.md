# Estado do projeto
## Feito
- Setup do vault e CLAUDE.md
- Escopo do MVP definido (bot Telegram, Mercado Livre, Python+SQLite)
- Visão do produto definida (memoria/produto/visao.md)
- Marca definida: nome Lowpoint, tom, personalidade (memoria/produto/marca.md)
- Index do vault criado (memoria/index.md)
- Branding board completo no Paper ("Lowpoint — Branding")
- Design system definido: paleta, tipografia, componentes, regras
- Logo final: wordmark "LOWPOINT." + avatar "L." + elemento secundário (ponto isolado)
- Imagens exportadas para memoria/design/
- Fluxo de design definido: Paper → aprovação → implementação
## Pendente
- Atualizar seção de logo do brand board no Paper (limite semanal atingido)
## Sprint atual
- Semana 1 (até 08/11): modelo de dados + coletor de preços ML rodando e guardando histórico
- **Feito:** schema Alembic, models SQLAlchemy, verdict.py, best_offer.py, PriceSource (ABC + MLCatalogSource + MockSource), 27 testes passando
- **Próximo:** subir Docker Postgres, rodar migração, coletor agendado com dados reais
## Plano até Black Friday
- Semana 2 (até 15/11): bot Telegram — /adicionar /lista /remover + alerta de preço-alvo
- Semana 3 (até 22/11): veredito real/maquiado, testes, bot rodando 24/7
- Pós-BF: telas no Paper, dashboard, landing, deploy, README
