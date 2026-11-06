# Frontend — implementação da landing aprovada

2026-11-05. Lucas aprovou as seções finais e autorizou a implementação. Fonte: [Paper — fluxo A + B](https://app.paper.design/file/01M6CVG8YNRACRX74D729QY706/p-6-0), consultado por JSX e estilos computados. As imagens foram usadas apenas na revisão visual.

## Resultado

Landing local em `frontend/`, com React 19.3.1, TypeScript 7.0.2 e Vite 8.3.6. CSS próprio com os tokens e a tipografia aprovados. Arquivo de dependências com versões exatas e lockfile do npm público.

Hero editorial A → evidências → desfecho B → exemplo de alerta → como funciona → vereditos → FAQ → CTA GitHub. Navegação por âncoras, FAQ nativo com teclado e uma resposta aberta por vez, link de pular ao conteúdo, descrições dos gráficos e estados de foco visíveis.

Movimento: entrada da etiqueta, traço de investigação, carimbo, revelações em sequência e linha de preço desenhada conforme a rolagem. Sem bloquear a rolagem. A preferência `prefers-reduced-motion` desativa esses movimentos, exibe o gráfico inteiro e usa rolagem instantânea. Fontes locais e licenças incluídas.

- [Prévia desktop verificada](frontend/desktop.jpg)
- [Prévia mobile verificada](frontend/mobile.jpg)
- [Guia de execução](../../frontend/README.md)

## Dados e limites

`frontend/src/data/demo-history.json` contém dados fictícios explícitos em centavos inteiros. Mantém os preços principais aprovados e pequenas variações anteriores como amostras, não como oscilações artificiais de interpolação. Eixo horizontal narrativo; mesma escala vertical entre as cenas. Curva monotônica com controles limitados ao intervalo de cada par de preços; termina na amostra atual. Testes Python conferem que o exemplo gera maquiado em 27/Nov e real em 02/Dez usando o motor do bot.

A landing não chama API de preços, banco ou Telegram. Comandos são exemplos. CTA final aponta para o GitHub, pois o bot continua em teste pessoal. Configuração e deploy do webhook Vercel preservados. Publicação do site não foi realizada.

## Verificação

- `npm run build`: TypeScript e build de produção passaram; saída em `frontend/dist/`.
- `npm test`: 5 testes passaram, incluindo interpolação sem extremos artificiais, escala compartilhada, percentuais e valores monetários.
- `python -m pytest -q`: 210 testes passaram; quatro avisos legados de SQLAlchemy no webhook. Após alterações paralelas no backend, repetidos os dois testes novos de concordância da landing: passaram.
- Navegador: revisados 320, 390, 768, 1024 e 1440 px. Sem overflow horizontal na versão final. Ajustados quebra do título, posição do carimbo, ordem das legendas mobile, largura do gráfico e tamanho dos marcadores.
- Âncoras para história e alerta testadas; FAQ abre, fecha por Enter e mantém uma resposta aberta. Console sem erros observados.
- Movimento reduzido: implementação revisada em CSS e hooks; a ferramenta de navegador disponível não oferece emulação dessa preferência, então não foi validado com emulação ativada.
- GitHub Actions passou: [execução 42149176633](https://github.com/luthhop/lowpoint/actions/runs/42149176633), commit a157898. Jobs build e story concluídos com sucesso (12s e 25s).

## Retomada

Rodar `cd frontend`, `npm ci` e `npm run dev`; prévia em http://127.0.0.1:5173/. Para produção local, `npm run build` e `npm run preview`.

Próxima decisão: publicação estática em projeto separado, usando raiz `frontend`, build `npm run build` e saída `dist`. Não substituir o `vercel.json` do webhook.

Durante a implementação surgiram alterações paralelas em `lowpoint/verdict.py`, `lowpoint/telegram/formatter.py` e `tests/test_landing_story.py`. Não foram feitas pelo Codex nesta etapa e foram preservadas fora do commit do frontend.
