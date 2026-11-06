# Referências da landing — 2026-11-05

Referências enviadas por Lucas como régua de qualidade, autenticidade e animação. Não copiar identidade, composição ou assets.

## Inspeção direta

- [Money Flow](https://landing-page-money-flow.vercel.app/): hero com gravura urbana índigo, promessa grande e demonstração do Telegram; ao rolar, a cena passa a fundo escuro e o telefone permanece enquanto áudio, resposta e painel se destacam em etapas. Progresso e texto acompanham a demonstração. Inspecionados hero e primeiros dois atos da sequência.
- [FitFolio](https://www.fitfolio.com.br/): versão escura observada, acento laranja, composição de celulares em diferentes planos e fotos de pessoas sobrepostas. A seção de recursos permite alternar Treinos/Dieta/Streak/Comunidade; ao selecionar Dieta, imagem e texto mudam juntos. Inspecionados hero e interação Treinos → Dieta. A galeria em movimento é descrita na página, mas não foi avaliada visualmente nesta inspeção.

## Leitura de design

- Money Flow: continuidade entre cenas e demonstração concreta sustentam a promessa.
- FitFolio: produto em uso e presença humana comunicam a experiência; hierarquia de escala e profundidade dão personalidade.
- Padrão comum: imagens e movimento pertencem ao assunto do produto e ajudam a explicá-lo.

## Proposta para Lowpoint — ainda não aprovada

- Conceito: investigação de uma promoção. Linguagem editorial baseada na identidade Signage + Onyx existente.
- Hero: título curto e forte acompanhado de evidência de preço, legível também no celular. Reavaliar o wireframe v7, que esconde a demonstração no hero mobile.
- Cena principal: mesmo gráfico acompanha preço normal → inflação → falso desconto → desconto real. A etiqueta de desconto é confrontada com a linha do preço normal; o ponto Forest aparece com o veredito real.
- Telegram: a conclusão da história se transforma no alerta, mantendo o contexto do produto e dos valores.
- Movimento: concentrar a coreografia nessa sequência; leitura e navegação mais leves nas demais seções. Sem prender a rolagem; versão reduzida sem movimento preserva toda a informação.
- Lupa 3D, gravura e celular em perspectiva do wireframe são hipóteses, não requisitos. Avaliar se ajudam a narrativa antes de adotá-los.
- Não reaproveitar o acento laranja do FitFolio, o neon do Money Flow ou suas composições. Manter Archivo, Libre Franklin, IBM Plex Mono e semântica Forest/Ochre.

## Próximo passo

Desenhar hero e momentos-chave da história no Paper, com estados mobile e desktop e anotações de movimento. Paper aprova composição e estados; movimento será validado em protótipo no navegador após aprovação do design. CTA final depende da decisão de acesso público vs. vitrine do MVP pessoal.

## Material adicional enviado por Lucas

- [Repositório Money Flow](https://github.com/guithepc/money-flow). README e frontend/package.json consultados: frontend do aplicativo em React, TypeScript, Vite e Tailwind, com Recharts. A documentação o descreve como dashboard. Não foi identificado nesta inspeção o código responsável pela landing separada hospedada na Vercel; não atribuir a ela bibliotecas de animação com base nas dependências do dashboard.
- Prints de lives mostram numerosas explorações de símbolo de marca, diferentes heros e pranchas distintas para os momentos da demonstração. Observação limitada às imagens enviadas; os vídeos não foram assistidos.
- Consequência para o processo: comparar alternativas visuais antes de considerar a primeira proposta encerrada. Landing Investigação v1 é uma base de hierarquia e narrativa, ainda sem aprovação visual; explorar composição e um elemento visual próprio sem refazer a marca já aprovada.

## AceleraDev — referência técnica complementar

Lucas enviou [landing-page-aceleradev](https://github.com/guithepc/landing-page-aceleradev). A main contém o espelho do site WordPress antigo; a nova implementação está na [branch feature/v2](https://github.com/guithepc/landing-page-aceleradev/tree/feature/v2), pasta v2.

README da branch e [js/main.js](https://github.com/guithepc/landing-page-aceleradev/blob/feature/v2/v2/js/main.js) consultados diretamente em 2026-11-05. A página WordPress atual foi aberta, mas não representa a V2. A V2 não foi executada visualmente nesta inspeção.

- HTML/CSS/JS sem framework, segundo o README; globo com d3/topojson em script separado.
- main.js confirma revelações com IntersectionObserver e atraso entre elementos; contadores com requestAnimationFrame; etapas ativadas conforme sua posição na tela; parallax leve; faixa horizontal sincronizada com rolagem, sticky e indicador de progresso.
- Consulta prefers-reduced-motion para desativar parte dos movimentos. Não se trata de auditoria completa de acessibilidade.
- Mural de prints usa repetição de conteúdo para loop e dialog para ampliar evidências.

Aplicação ao Lowpoint: útil para estudar ligação entre rolagem e estados, progressão e ampliação de evidências. Manter Money Flow e FitFolio como referências visuais principais. Não adotar globo, mural de alunos ou linguagem comercial por associação com o autor: cada elemento deve servir ao histórico de preços e ao veredito.
