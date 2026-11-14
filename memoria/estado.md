# Estado do projeto
## Sprints 1 e 2 — completas
- Coletor ML catálogo, veredito, anti-golpe; bot /adicionar /lista /remover /apelido; webhook Vercel
- GitHub: https://github.com/luthhop/lowpoint; 20 watches ativos (PS5, LG 27", AOC 27" + 17 de análise)
## Sprint 3 — em andamento
- Pós-pico: ≤3% SEGURA (template C), 3–5% MONITORANDO, ≥5% + menor histórico = PODE IR
- Tick ATIVO: cron externo horário às :45 → /api/tick → workflow_dispatch + aviso se coleta >90 min (verificado 14/11)
- Aviso falso a cada ~2h (11–13/11): gap 55→25 min p/ batida horária (14/11). Vigiar: scripts/audit_collections.py --hours N
- 564 testes Python (14/11) + 5 frontend; landing App.tsx ainda com linha antiga do PODE IR
- Anti-spam novo (1/h, ≥3%, maquiado 1/24h, tipo mudou) + cron só :17 — LOCAL, sem commit/push (14/11 19h)
## Produtos de análise BF (14/11)
- 17 em memoria/analise-bf.md (watches 6–22), alvo 50%. Neon: coluna silent aplicada e os 17 com silent=true (14/11 19:04)
- Silêncio só vale após push (coletor roda o main). Limite agora 3/20 normais, 17/40 silenciosos. Coleta ~40 chamadas ML
## Design e landing
- Landing publicada: https://lowpoint-web.vercel.app; projeto lowpoint-web, raiz frontend
- Lucas quer animações com mais impacto — ritmo etiqueta → histórico → SEGURA → desconto real → alerta
- Web = vitrine ao vivo (só leitura) + beta por convite; CTAs "Ver o código"/"Quero testar"; wireframe v10, falta destino do convite
## Próximo
- PRÓXIMO: revisar e dar push do silencioso + anti-spam ANTES de 21/11 (os 17 completam 7 dias)
- Decidir sobre reativar LG 32" (watch 1, inativo desde 09/11; agora cabe, 3/20); animações; dashboard pós-BF
