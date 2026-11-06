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
- 210 testes Python + 5 frontend passaram; build TypeScript/Vite passou; 4 avisos legados SQLAlchemy
- Simulação sem rede/banco: scripts/preview_recovered_hike.py
- Textos e critérios: memoria/design/validacao-pos-pico.md
## Design e landing
- Branding completo no Paper; conexão Paper operacional no Codex
- Landing completa aprovada e implementada em frontend/ (React/TypeScript/Vite); design/frontend-implementacao.md
- Lucas aprovou A na abertura + B no desfecho; fluxo contínuo desktop/mobile no Paper; design/landing-fluxo-consolidado.md
## Retomada
- Próximo: revisão da prévia local e decisão de publicação estática; webhook Vercel preservado
- Alterações paralelas no backend preservadas fora do commit frontend; remover “Fone Teste” (watch id=3) ainda pendente
