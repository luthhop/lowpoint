# Estado do projeto
## Sprints 1 e 2 — completas
- Coletor ML catálogo, veredito, anti-golpe; bot /adicionar /lista /remover /apelido; webhook Vercel
- GitHub: https://github.com/luthhop/lowpoint; 20 watches ativos (PS5, LG 27", AOC 27" + 17 de análise)
- LG 32" (product 1, watch 1) INATIVO desde 09/11 07:59: não é coletado, histórico parado em 6 dias
## Sprint 3 — em andamento
- Pós-pico: ≤3% SEGURA (template C), 3–5% MONITORANDO, ≥5% + menor histórico = PODE IR
- Tick ATIVO: cron externo horário às :45 → /api/tick → workflow_dispatch + aviso se coleta >90 min (verificado 14/11)
- Aviso falso a cada ~2h (11–13/11): gap 55→25 min p/ batida horária (14/11). Vigiar: scripts/audit_collections.py --hours N
- 507 testes Python (14/11) + 5 frontend; landing App.tsx ainda com linha antiga do PODE IR
## Produtos de análise BF (14/11)
- 17 produtos em memoria/analise-bf.md, só p/ análise pós-BF. --apply 14/11 14:55: watches 6–22, alvo 50%, 1º ponto gravado (conferido READ ONLY)
- 20/20 watches = limite; sem vaga p/ LG 32" nem /adicionar. Coleta ~40 chamadas ML/execução. <7d de histórico: só alerta se bater alvo
## Design e landing
- Landing publicada: https://lowpoint-web.vercel.app; projeto lowpoint-web, raiz frontend
- Lucas quer animações com mais impacto — ritmo etiqueta → histórico → SEGURA → desconto real → alerta
- Web = vitrine ao vivo (só leitura) + beta por convite; CTAs "Ver o código"/"Quero testar"; wireframe v10, falta destino do convite
## Próximo
- PRÓXIMA TAREFA: silenciar os 17 de análise antes de 21/11 (quando completam 7 dias e o veredito deixa de ser só neutro)
- Decidir sobre reativar LG 32" (esbarra no limite de 20); animações da landing; dashboard pós-BF
