# Landing — seções finais para revisão

2026-11-05. Complemento do fluxo A + B aprovado por Lucas. “Como funciona”, vereditos, FAQ e CTA final aprovados por Lucas e implementados; ver [implementação do frontend](frontend-implementacao.md).

[Paper](https://app.paper.design/file/01M6CVG8YNRACRX74D729QY706/p-6-0) · [Desktop completo](landing-fluxo-desktop.png) · [Mobile completo](landing-fluxo-mobile.png)

## Como funciona

[Desktop](landing-como-funciona-desktop.png) · [Mobile](landing-como-funciona-mobile.png)

“Você escolhe. A gente fica de olho.”

1. Manda o link: produto de catálogo do Mercado Livre no Telegram.
2. Define teu alvo: quanto quer pagar; produto fica na lista.
3. Recebe o aviso: coletas programadas a cada hora, análise do alvo e histórico antes do alerta.

Demonstração usa /adicionar com o catálogo real MLB57081243 e alvo ilustrativo de R$ 3.300. Não executa o comando nem envia nada ao bot. Acesso atual em teste pessoal é informado.

## Vereditos

[Desktop](landing-vereditos-desktop.png) · [Mobile](landing-vereditos-mobile.png)

“Três respostas. Nenhuma pressão.”

- PODE IR: novo menor preço, pelo menos 5% abaixo do preço normal. Passa pelos critérios do Lowpoint.
- SEGURA: a queda parece maior do que é; o histórico não sustenta o desconto anunciado.
- MONITORANDO: falta histórico ou o preço ainda não atende aos critérios de desconto real; alvo atingido pode gerar aviso.

## FAQ — texto para aprovação

[Desktop](landing-faq-desktop.png) · [Mobile](landing-faq-mobile.png)

Todas as respostas estão abertas nas pranchas para revisão do conteúdo. Implementar como acordeão acessível, com botões, estados expandidos e navegação por teclado; a informação deve permanecer disponível com movimento reduzido.

### Já posso usar o bot?

Por enquanto, o Lowpoint está em teste pessoal, com acesso restrito. Você pode acompanhar o desenvolvimento e o código no GitHub.

### Funciona com qualquer link do Mercado Livre?

Nesta versão, usamos links de produtos de catálogo: aqueles com /p/MLB no endereço. Links de anúncios individuais ainda não são aceitos.

### Quando chega um alerta?

As coletas são programadas a cada hora. O bot confere o alvo e o histórico antes de avisar. O mesmo tipo de alerta só é reenviado se o preço cair abaixo do último aviso.

### E se ainda não houver histórico?

Antes de completar sete dias de monitoramento, o bot pode avisar que o alvo foi atingido, mas não afirma que encontrou um desconto real.

### Como trata ofertas suspeitas?

O Lowpoint compara os preços para filtrar ofertas muito abaixo do padrão e informa quando alguma foi ignorada. Vale conferir o vendedor e as condições da oferta.

### Você ganha comissão se eu comprar?

Hoje não há links de afiliado. A regra do projeto é que uma comissão nunca influencie o veredito.

## CTA e navegação

“Antes de comprar, confere a história.”

“O Lowpoint está em desenvolvimento. Acompanhe o código, as decisões e a evolução do projeto.”

Botão “Acompanhar no GitHub” aponta para https://github.com/luthhop/lowpoint. É o destino coerente com o acesso restrito atual, não uma decisão permanente de manter o produto fechado. Sem promessa de cadastro público, preço de plano ou tempo de onboarding.

Navegação desktop inclui Como funciona, Os vereditos, Perguntas e GitHub. Rodapés reposicionados após as novas seções. As âncoras se tornam funcionais na implementação.

## Revisão e próxima etapa

Seções revisadas individualmente em desktop e mobile: hierarquia, espaçamento, contraste, alinhamento e encaixe. Sem cortes; alturas fit-content. Nenhuma alteração no backend, banco ou Telegram.

Implementação concluída em React/TypeScript/Vite, com navegação e FAQ verificados no navegador. Revisão da prévia e publicação são as próximas etapas. Os gráficos do Paper permanecem esquemáticos; o frontend usa seu fixture explícito, validado contra o veredito real.
