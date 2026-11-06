# Landing — fluxo A + B

2026-11-05. Lucas aprovou a combinação: A como abertura, B como desfecho. Gostou das duas direções e pediu um gráfico menos rígido; o traço foi refinado antes desta consolidação.

[Paper — fluxo A + B](https://app.paper.design/file/01M6CVG8YNRACRX74D729QY706/p-6-0)

- [Desktop](landing-fluxo-desktop.png)
- [Mobile](landing-fluxo-mobile.png)

## Sequência consolidada

1. **Abertura editorial:** “Tem desconto que engana.” Etiqueta com −40%, comparação com o preço anterior e SEGURA.
2. **Evidências:** “O que a etiqueta não te conta.” Três datas do mesmo PS5: R$ 3.450 até 14/Nov; alta para R$ 6.000 em 15/Nov; falsa promoção a R$ 3.600 em 27/Nov.
3. **Desconto real:** em 02/Dez, R$ 3.200, 7% abaixo do normal e abaixo do alvo de R$ 3.300. Fundo Ink, mesma história no gráfico fluido e ponto Forest no novo mínimo. “O preço cai. A dúvida também.”
4. **Telegram:** trecho ilustrativo do alerta PODE IR e “O veredito chega. A decisão é tua.”
5. **Rodapé:** GitHub para acompanhar o desenvolvimento.

Hero tem CTA de rolagem para a história; desfecho tem CTA de rolagem para o exemplo do alerta. São demonstrações ilustrativas, sem envio ao Telegram ou consulta de produto. “Conhecer o projeto”/GitHub deve apontar para o repositório.

## Revisão

Pranchas contínuas desktop e mobile revisadas por screenshots, além da ponte e do desfecho em separado. Espaçamento, hierarquia, contraste, alinhamento e encaixe aprovados internamente. Repetição do cabeçalho e status bar removida do desfecho. Altura fit-content permite o fluxo completo. As alternativas originais e a v1 foram preservadas.

O fluxo estático foi consolidado após aprovação da combinação; seus novos detalhes de transição ainda estão sujeitos à revisão de Lucas. A animação não está implementada. A mesma série, escala e baseline deverão persistir no movimento. Curvas são esquemáticas e fictícias; não usar suas coordenadas como dados reais nem introduzir extremos artificiais na interpolação.

## Próxima etapa

- Completar seções de funcionamento, vereditos e FAQ, usando a narrativa consolidada como base e respeitando o estado real do produto.
- Fechar acesso público vs. vitrine pessoal e CTA de conversão; não prometer acesso aberto ao bot, “grátis” permanente ou cadastro em 30 segundos.
- Aprovar as seções restantes antes da implementação. Depois, definir stack e validar rolagem, mobile e movimento reduzido no navegador.
