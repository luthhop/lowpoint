# Estado do projeto
## Sprints 1 e 2 — completas
- Coletor ML catálogo, veredito, anti-golpe; bot /adicionar /lista /remover /apelido; webhook Vercel
- GitHub: https://github.com/luthhop/lowpoint; 20 watches ativos (PS5, LG 27", AOC 27" + 17 de análise)
## Sprint 3 — em andamento
- Pós-pico: ≤3% SEGURA (template C), 3–5% MONITORANDO, ≥5% + menor histórico = PODE IR
- Tick ATIVO: cron externo horário às :45 → /api/tick → workflow_dispatch + aviso se coleta >90 min (verificado 14/11)
- Aviso falso de atraso consertado (gap 25 min, 14/11). Vigiar: scripts/audit_collections.py --hours N
- No main (14/11): anti-spam, silencioso, cron só :17, recuo do pico ≥5% (SEGURA "e depois baixaram Y%", "em menos de um dia"). 587 testes + 5 frontend
## Produtos de análise BF (14/11)
- 17 em memoria/analise-bf.md (watches 6–22), alvo 50%. Neon: coluna silent aplicada e os 17 com silent=true (14/11 19:04)
- Silêncio ativo no main desde 2a8b271. Limite 3/20 normais, 17/40 silenciosos. Coleta ~40 chamadas ML. 0 maquiado enviado em produção
## Design e landing
- Landing publicada: https://lowpoint-web.vercel.app; projeto lowpoint-web, raiz frontend
- Lucas quer animações com mais impacto — ritmo etiqueta → histórico → SEGURA → desconto real → alerta
- Web = vitrine + beta por convite. No main (15/11): CTAs "Ver o código"/"Quero testar" (t.me/lowpointbr_bot?start=beta), PODE IR novo, FAQ (conta, alertas, beta), elipse presa ao −40%; bot com pedido de convite
## Próximo
- PRÓXIMO: conferir deploy da landing e do webhook; divergências restantes em memoria/design/landing-divergencias-v11.md
- Análise BF: pré-registro v1 + Emendas 1 (deal_ids+tags desde 15/11 09:45:29) e 2 (P5, exclusão por cobertura, P3 nos 18). Código em analysis/ (python -m analysis.report; deps em requirements-analysis.txt)
- Decidir sobre reativar LG 32" (watch 1, inativo desde 09/11; agora cabe, 3/20); animações; dashboard pós-BF
