# Estado do projeto
## Sprints 1 e 2 — completas
- Coletor ML catálogo, veredito, anti-golpe e coleta horária no GitHub Actions
- GitHub: https://github.com/luthhop/lowpoint; 2 produtos reais (monitor LG e PS5)
- Bot: /adicionar /lista /remover /apelido; alertas pelo coletor; webhook Vercel
## Sprint 3 — em andamento
- Correção pós-pico concluída: desconto ≤3% = maquiado; >3% segue regra normal
- baseline_price limpo nas contas; median_30d preservada; preço riscado não veta recuperação
- 4% = neutro; ≥5% + menor histórico = real; nota explica inflação anterior
- Neutro com alvo atingido não alega falta de histórico quando já há dados suficientes
- 210 testes Python + 5 frontend; build local e CI GitHub passaram
- Simulação sem rede/banco: scripts/preview_recovered_hike.py
## Design e landing
- Landing publicada: https://lowpoint-web.vercel.app; projeto lowpoint-web, raiz frontend, GitHub conectado
- Lucas comentou que animações podem ter mais impacto — ritmo etiqueta → histórico → SEGURA → desconto real → alerta
## Limpeza 2026-11-07
- "Fone Teste" (watch id=3) removido do banco: 1 watch + 1 alert + 5 price_history + 35 offer_snapshots + 1 product (MLB46141661)
- Diff descartado (≤ → <): mantido ≤ conforme decisoes.md. Borda 0.03 = maquiado confirmada nos testes
## Próximo
- Animações da landing (mais ritmo na sequência narrativa)
- Dashboard: pós-Black Friday
