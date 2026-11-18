# Estado do projeto
## Sprints 1–2 completas; Sprint 3 em andamento
- Coletor ML catálogo, veredito, anti-golpe, bot (/adicionar /lista /remover /apelido), webhook Vercel. GitHub luthhop/lowpoint. /adicionar <link> [alvo] [apelido] (18/11, no origin/main; migração b7c8d9e0f1a2 no Neon 12:52): watch sem alvo + sugestão de alvo após 7 dias; /lista conta dias da 1ª coleta
- 21 watches ativos (18/11 12:51): normais 2 PS5 e 23 Tab S10 Lite; 19 silenciosos = 4 LG 27", 5 AOC 27" + 17 de análise (memoria/analise-bf.md). Lacuna de coleta de 18/11 em decisoes.md. 0 maquiado enviado em produção
- Tick ATIVO: cron externo :45 → /api/tick → workflow_dispatch + aviso se coleta >90 min. Vigiar: scripts/audit_collections.py --hours N
## Análise BF
- Pré-registro v1 (tag pre-registro-v1) + Emendas 1 (deal_ids+tags desde 15/11 09:45:29), 2 (P5, cobertura, P3 nos 18) e 3 (17/11 19:47: exploratória Ref 1ª obs vs Ref B0)
- B0 fechada 17/11 14:50. Ref 1ª obs: 2 de 20 marcados (>5%): DualSense +15,7% (R$ 380 → 439,74), LG 27" −5,1%
- Código em analysis/ (python -m analysis.report; deps em requirements-analysis.txt); gráficos de publicação no main (d93d044)
## Web
- Landing publicada: https://lowpoint-web.vercel.app (projeto lowpoint-web, raiz frontend). Vitrine + beta por convite
- Termos ML (17/11): landing, README e bot conformes e publicados (7ecc137): nome só no aviso 4.1 do rodapé; /ao-vivo conforme no grupo do painel (5.2 indisponível, 5.3 frequência)
- Painel ao vivo (15/11, COMMIT LOCAL, SEM PUSH — Lucas confere os Termos de Desenvolvedores do ML antes de publicar preços):
  - GET /api/painel (lowpoint/painel.py, api/painel.py, vercel.json): 20 da allowlist, READ ONLY, cache 1h CDN, memo 5 min
  - /ao-vivo/: Ink/Muted, sem veredito, "referência fecha em 17/11" até a B0 fechar; landing com subtítulo, bloco-chamada e reforço
  - Local: scripts/painel_local.py + npm run dev. Deploy: VITE_PAINEL_URL=https://lowpoint-theta.vercel.app/api/painel no lowpoint-web
## Próximo
- Lucas decide sobre os Termos do ML → push/deploy do painel (fora de :40–:50)
- Passar /ao-vivo pelo Paper; divergências em memoria/design/landing-divergencias-v11.md
- Reativar LG 32" (watch 1)? Animações; dashboard pós-BF
