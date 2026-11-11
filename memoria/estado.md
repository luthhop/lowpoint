# Estado do projeto
## Sprints 1 e 2 — completas
- Coletor ML catálogo, veredito, anti-golpe e coleta horária no GitHub Actions
- GitHub: https://github.com/luthhop/lowpoint; 4 produtos no banco (2 monitores LG, PS5, AOC)
- Bot: /adicionar /lista /remover /apelido; alertas pelo coletor; webhook Vercel
## Sprint 3 — em andamento
- Correção pós-pico concluída: desconto ≤3% = maquiado; >3% segue regra normal
- baseline_price limpo nas contas; median_30d preservada; preço riscado não veta recuperação
- 4% = neutro; ≥5% + menor histórico = real; nota explica inflação anterior
- Neutro com alvo atingido não alega falta de histórico quando já há dados suficientes
- 213 testes Python + 5 frontend (2026-11-10); faixa 4% = MONITORANDO testada
- SEGURA com pico: template C ("O anúncio diz", "em N dias" do início do pico)
- Backtest real 2026-11-10: 81 vereditos, 0 mudanças, 0 picos — histórico <14d não exercita o fix
## Design e landing
- Landing publicada: https://lowpoint-web.vercel.app; projeto lowpoint-web, raiz frontend, GitHub conectado
- Lucas comentou que animações podem ter mais impacto — ritmo etiqueta → histórico → SEGURA → desconto real → alerta
- Limpeza 2026-11-07: "Fone Teste" removido; mantido ≤ na borda 3%
## Próximo
- Animações da landing (mais ritmo na sequência narrativa)
- Dashboard: pós-Black Friday
