# Visão do Produto

## Frase-chave
"Os outros te mostram a promoção. O Lowpoint te diz se ela é de verdade."

## Problema
Grupos e apps de promoção mandam centenas de ofertas misturadas. O produto que você quer fica perdido ou você vê tarde demais. Pior: não dá pra saber se o desconto é real ou se o preço foi inflado antes.

## Solução
Bot pessoal no Telegram que monitora produtos específicos no Mercado Livre. Alerta quando o preço atinge o alvo e dá um veredito claro: desconto real ou maquiado, com base no histórico de preços.

## Dois modos de uso
- **Vigia (bot):** adicionar produto com preço-alvo e esquecer. O alerta chega destacado, impossível de ignorar.
- **Dashboard:** ver evolução de preço, menor histórico e verificar se o desconto do dia é legítimo.

## Para quem
Nicho na identidade, universal no uso. A marca fala com gente de tech/gamers que pesquisa preço e desconfia de promoção falsa. Mas qualquer pessoa que compra no Mercado Livre pode usar.

## Diferencial
Confiança. Juntar três coisas que ninguém junta:
1. Foco só no que você quer (sem feed de ofertas aleatórias)
2. Veredito claro sobre o desconto (real ou maquiado, com histórico)
3. Funciona direto no Telegram, sem instalar nada

## Sentimento
Segurança com vantagem. "Posso confiar e agir sem medo de estar sendo enganado. Enquanto os outros caem no '40% OFF' maquiado, eu compro no momento certo." Calma e confiante, nunca ansiosa. O Lowpoint não cria urgência — ele tira a ansiedade da compra.

## O que o Lowpoint NÃO é

### Limites permanentes
- Não é rede social (sem reviews, comunidade ou feed social)
- Não cria urgência falsa (sem contagem regressiva, sem "últimas unidades")
- Não vende nada. O Lowpoint protege, não empurra
- Se houver afiliado no futuro: a comissão nunca influencia o veredito

### Limites do MVP (podem mudar na Fase 2)
- Não é agregador — sem feed geral (Fase 2: feed filtrado por veredito, só descontos reais)
- Não é comparador de lojas — só Mercado Livre (Fase 2: outras lojas)

## Cenário de sucesso (6 meses)
1. **Uso real:** comprar os itens do setup no preço certo, evitar pelo menos um desconto maquiado. Não é projeto de gaveta.
2. **Projeto que representa:** GitHub com README, arquitetura e testes de nível profissional. Post no LinkedIn com análise de dados coletados (ex.: "quantos descontos de Black Friday eram reais?"). Abrir conversas de entrevista.
3. **Outras pessoas pediram pra usar:** amigos usando, provando que resolve uma dor real.

## Princípios inegociáveis
1. **Visual autêntico, nunca genérico.** Cada escolha de design tem regra e motivo. Money Flow é a régua de qualidade, não modelo para copiar. Superar em testes, CI, migrações, segurança, README e dados.
2. **Qualidade antes de velocidade.** Sem pressa e sem atalho. Se for para fazer, é para ficar bom.
3. **Feito para o Brasil.** Português, R$ 1.234,56, mobile-first.
4. **O processo também é o produto.** O vault de memória fica no repositório, mostrando como o Lowpoint foi construído com IA.

## Roadmap
- **MVP (até 2026-11-27):** Bot Telegram, Python + python-telegram-bot + SQLite, uso pessoal
- **Fase 2:** Site com landing page + painel, design no Paper, publicar GitHub/LinkedIn

## Telas previstas (Fase 2)
1. Landing page
2. Login / cadastro
3. Onboarding (conectar o Telegram)
4. Dashboard (produtos monitorados, histórico de preço, veredito)
5. Aparência das mensagens do bot

## Fluxo de design
Todo UI/UX do frontend é desenhado no Paper antes de ser implementado, seguindo o branding board. Nenhuma tela é implementada sem design aprovado.

1. Desenhar no Paper
2. Aprovação do Lucas
3. Implementação seguindo o design
