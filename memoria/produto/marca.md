# Marca

## Nome
**Lowpoint** — "o ponto mais baixo", o menor preço histórico. Palavras reais em inglês, curtas, juntas, soando como marca única (referências: Spotify, Money Flow).

## Logo
**LOWPOINT.** — wordmark em Archivo Black 900 uppercase + ponto Forest (#1B6B3A) como período final. Duplo sentido em português: "ponto" é o "point" do nome (o ponto mais baixo do preço) e o ponto final da frase (veredito dado, encerrado). "LOWPOINT." = o menor preço, e ponto final. O ponto verde é conquistado — só aparece quando o desconto é real.

### Avatar (Telegram)
**L.** — monograma L em Archivo Black branco sobre círculo Ink (#0A0A0A), com ponto Forest grande como período. Legível em 32px e 64px.

### Elemento secundário
**Ponto isolado** — ponto Forest grande posicionado embaixo ("low point") dentro de círculo Ink. Usar em: favicon, loading/spinner, animação do hero SVG do README. Não é logo, é elemento da marca.

## Personalidade
O amigo desconfiado que confere tudo antes de você gastar. Fala direto, com números sempre, emoji no máximo um e só quando faz sentido. Nunca empurra compra. O trabalho dele é te proteger, não vender.

## Tom de voz
Dados com atitude. Direto, com números, sem floreio.

### Exemplos de mensagens (Telegram)

**Alvo atingido (desconto real):**
```
✅ PODE IR · PS5 Digital · R$ 3.200,00

Bateu teu alvo de R$ 3.500,00. Esse é de verdade. Pode ir.
Menor preço em 47 dias, 18% abaixo do normal.

Preço normal: R$ 3.890,00
Menor anterior: R$ 3.280,00

Loja oficial · Com garantia
```

**Desconto real (sem alvo atingido):**
```
✅ PODE IR · Monitor LG 27" · R$ 1.449,00

Novo menor preço, 14% abaixo do normal. Esse é de verdade. Pode ir.

Preço normal: R$ 1.680,00
Menor anterior: R$ 1.520,00

Loja oficial · Com garantia
```

**Desconto maquiado:**
```
⚠ SEGURA · PS5 Digital · R$ 3.600,00

O anúncio diz 40% OFF (de R$ 6.000,00).
Preço normal no último mês: R$ 3.450,00.
Subiram pra baixar. Preço subiu 9% nas 2 semanas antes da "queda" (era R$ 3.300,00).

Com garantia · Vendedor não-oficial
```

**Alvo atingido + maquiado:**
```
⚠ SEGURA · PS5 Digital · R$ 3.400,00

Bateu teu alvo de R$ 3.500,00, mas subiram pra baixar.
O anúncio diz 39% OFF (de R$ 5.600,00).
Preço normal no último mês: R$ 3.450,00.

Com garantia · Vendedor não-oficial
```

**Rodapés (adicionados conforme contexto):**
- `Sem garantia informada` — destaque (sem emoji), sempre que aplicável
- `Vendedor não-oficial` — discreto, só como detalhe
- `Ignorei um anúncio de R$ 2.399,00, bem abaixo do normal: costuma ser golpe.` — quando houver suspeita

Todos os alertas incluem botão inline "Ver oferta" com link do anúncio exato.

### Regras de tom
- Sempre com dados concretos (preço, percentual, período)
- Emoji: no máximo um, só quando faz sentido
- Nunca cria urgência ("CORRE!", "últimas unidades!")
- Nunca empurra compra — protege, não vende
- Linguagem em português do Brasil, informal mas precisa

## Sentimento da marca
Segurança com vantagem. Calma e confiante, nunca ansiosa. "Posso confiar e agir sem medo. Enquanto os outros caem no desconto maquiado, eu compro no momento certo."

## Identidade de público
Nicho na identidade (tech/gamers que desconfiam de promoção falsa), universal no uso.

## Identidade visual

### Direção
Signage (editorial) + Onyx (disciplina brutalista). Preto e tipografia fazem o trabalho. Cor é conquistada, não decorativa.

### Paleta
| Token   | Hex       | Papel                                                    |
|---------|-----------|----------------------------------------------------------|
| Ink     | `#0A0A0A` | Texto, bordas, logo. Cor padrão de tudo                  |
| Paper   | `#F5F5F0` | Superfícies, cards, fundo de componentes                 |
| White   | `#FFFFFF` | Fundo da página e do board                               |
| Forest  | `#1B6B3A` | Só desconto verificado como real. Conquistado, não decorativo |
| Ochre   | `#7A5A10` | Só veredito "segura" (maquiado). Sem vermelho            |
| Muted   | `#999999` | Labels, metadados, timestamps                            |

Contrastes WCAG AA verificados: Forest 5.4:1, Ochre 5.2:1 (sobre Paper #F5F5F0).

### Tipografia
| Família          | Peso    | Papel                                  |
|------------------|---------|----------------------------------------|
| Archivo          | 900     | Display, títulos, manchetes. Sempre uppercase. Tracking -0.02em |
| Libre Franklin   | 400/600 | Corpo, descrições, vereditos            |
| IBM Plex Mono    | 500/700 | Dados, preços, labels. Uppercase + letter-spacing 0.06em para labels |

### Regras de design
- Radius 0 em tudo
- Sem gradientes, glassmorphism, Inter
- Borda lateral como indicador semântico (verde = real, ocre = maquiado)
- Preços sempre em IBM Plex Mono, formato R$ 1.234,56
- Mobile-first: o alerta chega no celular
- Sem amarelo (ML), laranja (Shopee/Amazon), roxo gradiente (IA genérica)
- Money Flow como régua de qualidade, não modelo para copiar

### Componentes-chave
- Card de alerta real: borda esquerda verde, dados + veredito "Pode ir"
- Card de alerta maquiado: borda esquerda ocre, dados + veredito "Segura"
- Selos de veredito: PODE IR (verde), SEGURA (ocre), MONITORANDO (ink)
- Mini gráfico de histórico de preço (sparkline)

### Arquivos de design
- Board completo: `memoria/design/brand-board.png`
- Explorações: `memoria/design/exploracao-*.png`
- Arquivo Paper: "Lowpoint — Branding"
