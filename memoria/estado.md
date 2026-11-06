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
- 208 testes passaram (46 landing); 4 avisos legados SQLAlchemy no webhook
- Simulação sem rede/banco: scripts/preview_recovered_hike.py
- Textos e critérios: memoria/design/validacao-pos-pico.md
## Design e landing
- Branding completo no Paper; conexão Paper operacional no Codex
- Landing completa no Paper: funcionamento, vereditos, FAQ e CTA final; design/landing-secoes-finais.md; aguardam aprovação de Lucas
- Lucas aprovou A na abertura + B no desfecho; fluxo contínuo desktop/mobile no Paper; design/landing-fluxo-consolidado.md
## Retomada
- Lote validado: correções pós-pico + textos e documentação; push autorizado por Lucas
- Remover “Fone Teste” (watch id=3) continua pendente; sem mudanças em produção nesta sessão
