# LOWPOINT. — Frontend

Landing responsiva implementada a partir do design aprovado no [Paper](https://app.paper.design/file/01M6CVG8YNRACRX74D729QY706/p-6-0). React + TypeScript + Vite. Fontes Archivo, Libre Franklin e IBM Plex Mono servidas localmente, com as licenças em `public/licenses/`.

## Rodar

Node.js 26 e npm. Na pasta `frontend/`:

```bash
npm ci
npm run dev
```

Prévia: http://127.0.0.1:5173/. O servidor fica restrito ao loopback.

```bash
npm test          # testes de preços e interpolação
npm run build    # TypeScript + bundle de produção em dist/
npm run preview  # servir dist/ em http://127.0.0.1:4173/
```

Da raiz do repositório, `python -m pytest tests/test_frontend_story.py -q` verifica que a história ilustrativa continua produzindo SEGURA e PODE IR no motor real do bot.

## Estrutura

- `src/App.tsx`: seções da landing, navegação, demonstração e FAQ nativo.
- `src/styles.css`: tokens do Paper, layouts responsivos, estados e movimento reduzido.
- `src/components/PriceChart.tsx`: gráfico SVG que se ajusta ao tamanho real do contêiner.
- `src/lib/price-curve.mjs`: curva cúbica monotônica, formatação e percentuais.
- `src/data/demo-history.json`: exemplo fictício; valores monetários em centavos inteiros.
- `src/hooks/useMotion.ts`: revelações e desenho da linha conforme a rolagem, com limpeza de observers/listeners.
- `tests/`: testes sem navegador, rede ou banco, com o test runner do Node.

## Comportamento

O exemplo usa os marcos aprovados: preço normal R$ 3.450, pico R$ 6.000, falsa promoção R$ 3.600 e novo mínimo R$ 3.200. Pequenas variações anteriores também são dados fictícios explícitos no fixture, não distorções introduzidas pela curva. O eixo horizontal organiza etapas da narrativa e não representa uma escala linear de dias. A escala vertical é compartilhada entre os gráficos. A interpolação não ultrapassa os valores de cada intervalo e o marcador fica na última amostra.

Navegação por âncoras; links externos para o GitHub; FAQ com `details`/`summary`, teclado e apenas uma resposta aberta; link para pular ao conteúdo; gráficos com descrição acessível. `prefers-reduced-motion` desativa animações, rolagem suave e revelação progressiva do gráfico.

## Escopo e publicação

Esta é uma vitrine do projeto em teste pessoal: não há cadastro público, consulta de preços ao vivo ou conexão com o bot/banco. Os comandos são demonstrações; clicar nos CTAs nunca envia mensagens ao Telegram.

O `vercel.json` da raiz pertence ao webhook Python e foi preservado. Para publicar esta landing em um projeto estático separado, usar `frontend` como diretório raiz, comando `npm run build` e saída `dist`. O build não exige credenciais ou variáveis do backend. Publicado em https://lowpoint-web.vercel.app no projeto `lowpoint-web`, conectado ao GitHub `luthhop/lowpoint`. Raiz `frontend`, Node 26.x, instalação `npm ci`, build `npm run build`, saída `dist`. Deploy inicial autorizado por Lucas e verificado com HTTP 200 e navegador público. Próximas publicações usam a integração com GitHub e o diretório raiz `frontend`.

CI: `.github/workflows/frontend.yml` verifica o build, os testes do Node e a concordância do fixture com o motor Python.
