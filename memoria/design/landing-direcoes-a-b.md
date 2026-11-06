# Landing — direções A e B

2026-11-05. Duas alternativas solicitadas por Lucas, mantendo a identidade já aprovada. A v1 foi preservada. Aguardam escolha e aprovação visual; não implementar sem essa aprovação.

[Página no Paper](https://app.paper.design/file/01M6CVG8YNRACRX74D729QY706/p-5-0)

## A — Investigação editorial

- [Desktop](landing-a-desktop.png), 1440×900; [mobile](landing-a-mobile.png), 390×844.
- Headline: “Tem desconto que engana.” Etiqueta preta inclinada, marca de investigação em ocre, recorte do histórico e carimbo SEGURA.
- Branco, preto e Paper predominam. Ocre serve ao veredito negativo, Forest só no ponto do wordmark.
- Movimento proposto: etiqueta aparece primeiro; histórico revela o preço anterior; comparação destaca +R$ 150; carimbo conclui. Movimento reduzido mostra o estado completo.
- CTA “Ver a história desse preço” rola para a demonstração fictícia; não abre consulta de produto.

## B — O ponto mais baixo

- [Desktop](landing-b-desktop.png), 1440×900; [mobile](landing-b-mobile.png), mínimo de 390×844, altura fit-content.
- Headline: “O preço cai. A dúvida também.” Fundo Ink, tipografia branca e gráfico aberto atravessando a composição. A linha fica Forest no segmento final e chega ao ponto do novo mínimo.
- PODE IR em branco sobre Forest para legibilidade; preço atual em branco. Nenhum acento adicional.
- Movimento proposto: linha progride com a história; preço anterior permanece como referência; no novo mínimo, ponto e selo aparecem. Não animar números de preço como se fossem preços reais ao vivo.
- CTA “Acompanhar essa história” rola para a demonstração fictícia.

## Revisão e limites

Quatro pranchas revisadas por screenshots: hierarquia, espaçamento, alinhamento, contraste e encaixe. Corrigidos preço riscado parcialmente coberto na A mobile, status bar na B mobile, quebra do título, altura e contraste do selo na B. Nenhum conteúdo cortado na revisão final.

Gráficos ainda esquemáticos; implementar escalas e série a partir dos dados dos testes. Exemplos explicitamente fictícios: PS5, preço normal R$ 3.450, pico R$ 6.000, falsa promoção R$ 3.600, novo mínimo R$ 3.200. Sem promessa de cadastro público, gratuidade permanente ou acesso aberto ao bot.

Recomendação de design: A como abertura por demonstrar o problema imediatamente; considerar a composição B como desfecho da história. É recomendação, não decisão aprovada por Lucas. Animações ainda não implementadas.

Próximo passo: Lucas escolher a direção; fechar narrativa e conversão; expandir a landing aprovada antes de implementar o frontend.

## Revisão do traço — feedback de Lucas

Lucas gostou das duas composições, mas não do gráfico com segmentos retos. Após autorizar o refinamento, os quatro gráficos foram redesenhados com curvas Bézier, transições menos bruscas, pequenas oscilações ilustrativas e marcadores de preço mais delicados. A B ganhou referências de 15/Nov e 27/Nov junto à linha. A paleta, os textos e os valores principais permanecem os mesmos.

Desktop e mobile revisados por screenshots: contraste, hierarquia, espaçamento, alinhamento e encaixe mantidos, sem cortes ou sobreposição nova. Exports deste documento atualizados. As curvas são esquemas visuais fictícios, não interpolação validada do histórico dos testes; o frontend precisa usar a série real, sem introduzir oscilações ou extremos artificiais. Ainda aguardamos aprovação do refinamento visual; nenhuma animação implementada.
