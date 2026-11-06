# Landing — Investigação v1

2026-11-05. Lucas aprovou a direção conceitual baseada nas referências; estas primeiras composições ainda aguardam revisão visual. Nenhum frontend implementado.

[Página no Paper](https://app.paper.design/file/01M6CVG8YNRACRX74D729QY706/p-4-0)

## Pranchas

- [Hero desktop](landing-v1-hero-desktop.png): 1440×900. Título “Parece promoção. Será?”, comparação de preços, gráfico e carimbo SEGURA.
- [Hero mobile](landing-v1-hero-mobile.png): 390×844. A evidência permanece visível, com preço anterior e atual, sem depender do celular em perspectiva.
- [História do preço](landing-v1-historia.png): 1440×900. Quatro estados apresentados lado a lado para revisão; não é a proposta de quatro colunas fixas na implementação.
- [Desconto real mobile](landing-v1-desconto-real-mobile.png): 390×844. Desfecho da história e trecho do alerta PODE IR.

## Identidade e conteúdo

Archivo 900, Libre Franklin 400, IBM Plex Mono 500/700. White #FFFFFF, Ink #0A0A0A, Paper #F5F5F0, Forest #1B6B3A e Ochre #7A5A10. Forest semântico para o desconto real, além do ponto do wordmark aprovado.

Série ilustrativa existente: preço normal R$ 3.450 → pico R$ 6.000 → falsa promoção R$ 3.600 → novo mínimo R$ 3.200. Todos os exemplos identificados como fictícios. Gráficos de conceito ainda esquemáticos: implementar a série e escalas a partir dos dados dos testes, sem extrair coordenadas das imagens.

CTA de exploração: “Investigar um desconto” deve rolar para a história ilustrativa, não abrir uma consulta de produto. Validar clareza do rótulo antes da implementação. “Conhecer o projeto”/GitHub aponta para o repositório; não promete acesso público ao bot, que hoje tem allowlist.

Os cartões usam trechos do alerta para explorar composição; não representam o texto completo do Telegram. Para implementar, usar o formatter e a validação pós-pico como fonte da verdade.

## Coreografia proposta — validar no navegador

1. Entrada: headline e comparação surgem em uma sequência curta; leitura disponível imediatamente. Sem animação contínua do preço.
2. História desktop: um gráfico acompanha a rolagem dentro da seção, enquanto quatro momentos avançam no fluxo normal. A mesma escala e baseline persistem.
3. Inflação: novo segmento chega ao pico; preço riscado aparece junto do contexto temporal.
4. Fachada: queda para R$ 3.600, comparação com R$ 3.450, diferença +R$ 150 e carimbo SEGURA. O gráfico precisa explicar o veredito antes do selo.
5. Desconto real: segmento final cruza o preço normal, ponto Forest marca o novo mínimo e surge PODE IR. A conclusão leva ao exemplo do alerta no Telegram.
6. Mobile: gráfico compacto acompanha os atos apenas se houver altura útil; caso contrário, estados seguem no fluxo. Nenhuma rolagem bloqueada ou evidência escondida.
7. Movimento reduzido: gráficos e textos completos e estáticos, em ordem de leitura. O conteúdo não depende de progresso animado para ficar acessível.

## Revisão visual

Desktop e mobile revisados por screenshots: espaçamento, hierarquia, contraste, alinhamento e encaixe aprovados internamente; sem cortes. Repetição dos quatro estados é intencional no storyboard; composição final varia com transição para o alerta. Ajustada a quebra do título no desfecho mobile.

## Pendências

- Aprovação visual de Lucas para o hero e a história.
- Fechar CTA de conversão, modelo de acesso, subtítulo final e FAQ.
- Depois da aprovação, definir stack frontend e implementar protótipo responsivo de movimento, antes de expandir toda a landing.
