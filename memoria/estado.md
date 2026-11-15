# Estado do projeto
## Sprints 1–2 completas; Sprint 3 em andamento
- Coletor ML catálogo, veredito, anti-golpe, bot (/adicionar /lista /remover /apelido), webhook Vercel. GitHub luthhop/lowpoint
- 20 watches ativos (PS5, LG 27", AOC 27" + 17 silenciosos de análise, memoria/analise-bf.md). 0 maquiado enviado em produção
- Tick ATIVO: cron externo :45 → /api/tick → workflow_dispatch + aviso se coleta >90 min. Vigiar: scripts/audit_collections.py --hours N
## Análise BF
- Pré-registro v1 (tag pre-registro-v1) + Emendas 1 (deal_ids+tags desde 15/11 09:45:29) e 2 (P5, cobertura, P3 nos 18)
- Código em analysis/ (python -m analysis.report; deps em requirements-analysis.txt); gráficos de publicação no main (d93d044)
## Web
- Landing publicada: https://lowpoint-web.vercel.app (projeto lowpoint-web, raiz frontend). Vitrine + beta por convite
- Painel ao vivo (15/11, COMMIT LOCAL, SEM PUSH — Lucas confere os Termos de Desenvolvedores do ML antes de publicar preços):
  - GET /api/painel (lowpoint/painel.py, api/painel.py, vercel.json): 20 da allowlist, READ ONLY, cache 1h CDN, memo 5 min
  - /ao-vivo/: Ink/Muted, sem veredito, "referência fecha em 17/11" até a B0 fechar; landing com subtítulo, bloco-chamada e reforço
  - Local: python scripts/painel_local.py + npm run dev (proxy). Feita direto no código; Paper opcional
  - Deploy: VITE_PAINEL_URL=https://lowpoint-theta.vercel.app/api/painel no lowpoint-web (frontend/README.md)
## Próximo
- Lucas decide sobre os Termos do ML → push/deploy do painel (fora de :40–:50)
- Passar /ao-vivo pelo Paper; divergências em memoria/design/landing-divergencias-v11.md
- Reativar LG 32" (watch 1)? Animações; dashboard pós-BF
- /adicionar <link> [alvo] [apelido] + watch sem alvo + sugestão de alvo após 7 dias: aprovado 18/11, migração b7c8d9e0f1a2 aplicada no Neon (12:52), push no origin/main. /lista conta dias da 1ª coleta. Watches (18/11 12:51): 2 PS5 e 23 Tab S10 Lite normais; 4 e 5 reativados como silent (19 silenciosos). Lacuna de coleta em decisoes.md
