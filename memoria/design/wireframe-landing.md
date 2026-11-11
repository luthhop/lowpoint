# Wireframe — Landing Page Lowpoint (v8)

> Validado contra o código corrigido em `lowpoint/verdict.py` e `lowpoint/telegram/formatter.py`.
> Teste: `tests/test_landing_story.py` — 47 passed, 0 failed (total: 211).
> Mudanças v8 (2026-11-10): SEGURA com pico usa template C — "O anúncio diz X% OFF (de R$ …)" e "Subiram X% em N dias", N contado do início do pico. Texto conferido por teste de igualdade exata.
> Mudanças v7: recuperação >3% segue regra normal sobre baseline limpo; nota pós-pico no alerta. Validação: [cenários 4%, 10%, 20%](validacao-pos-pico.md).
> Mudanças v6: "Preço riscado" em vez de "O anúncio diz", "há N dias" (não "em"), floor() no %, baseline_price separado de median_30d, FACHADA_THRESHOLD=3%.

---

## DADOS DO EXEMPLO (fonte da verdade = teste)

> Exemplo ilustrativo. Preços e datas fictícios. Produto ID: MLBEX00001.

| Momento | Preço | Contexto |
|---|---|---|
| Ago 1 – Nov 14 | R$ 3.450 | Preço normal estável |
| Nov 15 – Nov 26 | R$ 6.000 | Markup silencioso (+74%) |
| Nov 27 (Black Friday) | R$ 3.600 | "40% OFF" — maquiado |
| Nov 28 – Dez 1 | R$ 3.600 | Pós-BF estável |
| Dez 2 | R$ 3.200 | Desconto real (-7% do normal) |

- **Produto**: PS5 Digital Edition
- **Alvo do usuário**: R$ 3.300
- **Golpe ignorado**: R$ 1.899 (abaixo de 60% da mediana = R$ 2.070)
- **Produto ID fictício**: MLBEX00001

---

## TEXTO EXATO DOS ALERTAS (gerado pelo código corrigido)

### Alerta SEGURA (27/Nov) — `alert_type: verdict_maquiado`

```
⚠ SEGURA · PS5 Digital Edition · R$ 3.600,00

O anúncio diz 40% OFF (de R$ 6.000,00).
Antes de subir, custava R$ 3.450,00.
Subiram 74% em 12 dias e baixaram de volta. Tá R$ 150,00 mais caro que antes. Segura.

Vendedor não oficial · Com garantia
```
Botão: "Ver oferta"

### Alerta PODE IR (02/Dez) — `alert_type: target_hit`

```
✅ PODE IR · PS5 Digital Edition · R$ 3.200,00

Bateu teu alvo de R$ 3.300,00. Esse é de verdade. Pode ir.
Menor preço desde que começamos a monitorar, 7% abaixo do normal.
Subiram antes, mas mesmo assim tá 7% abaixo do preço normal.

Preço normal: R$ 3.450,00
Menor anterior: R$ 3.450,00

Loja oficial · Com garantia
Ignorei um anúncio de R$ 1.899,00, bem abaixo do normal: costuma ser golpe.
```
Botão: "Ver oferta"

---

## SEÇÕES DA LANDING

### HEADER (fixo, Ink #0A0A0A)
- Logo "LOWPOINT." à esquerda (Archivo 900, ponto Forest)
- Âncoras: "COMO FUNCIONA" · "VEREDITO" · "PERGUNTAS" (Plex Mono 500 uppercase)
- CTA direita: [pendente decisão]

---

### HERO (fundo White #FFFFFF)

**Layout**: Texto à esquerda (60%), celular com Telegram à direita (40%) inclinado em perspectiva 3D sutil. Atrás do celular, ilustração em gravura monocromática Ink (estilo editorial, referência própria).

**Eyebrow**: Plex Mono 500 Muted uppercase, letter-spacing 0.06em:
"MONITORAMENTO DE PREÇOS COM VEREDITO"

**Headline** (Archivo 900, Ink, ~56px desktop / ~36px mobile, tracking -0.02em):
"OS OUTROS TE MOSTRAM A PROMOÇÃO.
O LOWPOINT TE DIZ SE ELA É DE VERDADE."

**Subtítulo** (Libre Franklin 400, 18px): [pendente decisão — depende de web aberta vs. vitrine]

**CTA principal**: [pendente decisão]
**CTA secundário**: texto-link Muted: "Ver como funciona"
**Reforço**: [pendente decisão — "Grátis · sem cadastro de cartão" depende do modelo]
**Chips** (3 pills, borda Ink 1px, radius 0, Plex Mono 500 12px): "Telegram" · "Dados públicos do ML" · "Código aberto"

**Animação**:
- Celular: fade-in + translateY(40px→0) ao carregar, 0.8s ease-out
- Gravura: parallax leve no scroll (translateY a 0.1x)
- Chips: stagger 0.1s entre si
- `prefers-reduced-motion`: sem translateY, sem parallax; só opacity 0→1 instantânea

**Mobile**: celular desaparece; headline ocupa 100% da largura; chips empilham em 2 linhas

---

### SEÇÃO "ANATOMIA DE UM DESCONTO FALSO" (scrollytelling)

**Transição de fundo**: White → Paper (#F5F5F0) gradual.
**Grid**: marcas "+" nos cruzamentos em Muted 20% opacity, 80px.

**Título**: Archivo 900 uppercase: "ANATOMIA DE UM DESCONTO FALSO"
**Subtítulo**: Libre Franklin 400 Muted: "Exemplo ilustrativo baseado em padrões reais."

**Layout desktop**: Texto dos atos à esquerda (50%). Gráfico de preço à direita (50%), position sticky.
**Layout mobile**: Gráfico no topo (100% largura, ~160px altura, sticky dentro da seção). Atos abaixo rolando normalmente.

**Gráfico de preço** (SVG, stroke Ink 2px, sem grid):
- Eixo X: "AGO" ... "NOV" ... "DEZ" (Plex Mono 500 Muted)
- Eixo Y: "R$ 3.000" ... "R$ 5.000" ... "R$ 6.000" (Plex Mono 500 Muted)
- Linha tracejada Muted: "ALVO: R$ 3.300"

**Ato 1 — PREÇO NORMAL**
Card borda esquerda Muted 2px:
- Label Plex Mono 500 Muted: "AGOSTO — NOVEMBRO"
- Manchete Archivo 900 24px: "R$ 3.450 HÁ 3 MESES"
- Texto Libre Franklin 400: "O PS5 Digital custa R$ 3.450 há 3 meses. Nenhuma promoção. Preço estável."
- Dado Plex Mono 500 Muted: "PREÇO NORMAL: R$ 3.450"

*Animação*: linha se desenha (stroke-dashoffset) até Nov 14, plana em ~R$ 3.450. 1.2s.
*Reduced-motion*: linha aparece completa com fade-in.

**Ato 2 — SOBE ESCONDIDO**
Card borda esquerda Ochre 2px:
- Label: "15 DE NOVEMBRO"
- Manchete: "SOBE PRA R$ 6.000. NINGUÉM PERCEBE."
- Texto: "Doze dias antes da Black Friday, o preço sobe 74%. Sem aviso, sem manchete."
- Dado: "MARKUP: +74% EM 12 DIAS"

*Animação*: linha sobe em curva até R$ 6.000, 0.8s ease-in. Etiqueta "R$ 6.000" fade-in no topo.
*Reduced-motion*: segmento aparece desenhado, etiqueta sem animação.

**Ato 3 — O FALSO DESCONTO**
Card borda esquerda Ochre 2px:
- Label: "27 DE NOVEMBRO — BLACK FRIDAY"
- Manchete: "'40% OFF' POR R$ 3.600"
- Texto: "O anúncio grita desconto. Preço riscado: R$ 6.000 (−40%). Mas o preço real subiu R$ 150 em relação a agosto. Você paga mais achando que pagou menos."
- Dado: "PREÇO ANTES DO MARKUP: R$ 3.450 · AGORA: R$ 3.600 · DIFERENÇA: +4%"

*Animação*: linha desce até R$ 3.600, 0.6s. Etiqueta "40% OFF" em Ochre com risco diagonal. Carimbo "SEGURA" (rotação -5°, borda Ochre 3px, Plex Mono 700 Ochre) bate com impacto (scale 1.2→1.0, 0.15s).
*Reduced-motion*: carimbo aparece estático sem scale.

**Ato 4 — O DESCONTO REAL**
Card borda esquerda Forest 2px:
- Label: "2 DE DEZEMBRO"
- Manchete: "R$ 3.200. ESSE É DE VERDADE."
- Texto: "Abaixo do preço normal, abaixo do alvo. Menor preço desde que começamos a monitorar. O Lowpoint diz: pode ir."
- Dado: "DESCONTO REAL: -7% · MENOR PREÇO DESDE O INÍCIO DO MONITORAMENTO"

*Animação*: linha desce até R$ 3.200. Ponto Forest (circle r=6) no lowpoint, 0.6s. Carimbo "PODE IR" (fundo Forest, texto Paper, mesmo impacto).
*Reduced-motion*: ponto e carimbo aparecem estáticos.

**Objeto marcante — LUPA 3D**
Posição: entre Ato 3 e Ato 4, centralizada, ou flutuando junto ao carimbo "SEGURA".
Visual: lupa 3D (render CSS com sombras ou SVG isométrico) examinando uma etiqueta de preço. Paleta: corpo em Ink, lente com reflexo sutil, etiqueta em Paper com "40% OFF" riscado em Ochre.
*Animação*: ao scroll entre atos 3 e 4, lupa rotaciona levemente (rotateY 10°→-5°, 0.6s) e a etiqueta sob ela muda de "40% OFF" para "SEGURA".
*Mobile*: lupa menor (64px), posicionada ao lado do carimbo, sem rotação 3D.
*Reduced-motion*: estática na posição final.

---

### SEÇÃO "O VEREDITO CHEGA ASSIM" (fundo White)

**Título**: Archivo 900 uppercase: "O VEREDITO CHEGA ASSIM"

**Layout desktop**: Celular centralizado em perspectiva 3D leve. Cartões flutuam para os lados.
**Layout mobile**: Sem celular. Conversa em formato de chat full-width com cartões empilhados.

**Conversa simulada**:

*Bolha do usuário* (alinhada à direita, fundo #E8E8E0):
`/adicionar mercadolivre.com.br/p/MLBEX00001 3300`

*Bolha do bot* (alinhada à esquerda, fundo Paper):
"PS5 Digital Edition adicionado. Alvo: R$ 3.300,00.
Preço atual: R$ 3.450,00. Te aviso quando chegar."

*Separador*: Plex Mono 500 Muted: "27 DE NOVEMBRO"

*Cartão flutuante "SEGURA"* (borda esquerda Ochre 4px, fundo Paper):
Texto EXATO do alerta gerado pelo código (ver seção acima).

*Separador*: "2 DE DEZEMBRO"

*Cartão flutuante "PODE IR"* (borda esquerda Forest 4px):
Texto EXATO do alerta gerado pelo código (ver seção acima).

**Animação**:
- Desktop: celular fade-in; bolhas stagger 0.3s; cartão SEGURA desliza esquerda (translateX -60px); cartão PODE IR desliza direita (+60px). Sombra offset-y 4px blur 16px rgba(0,0,0,0.08).
- Mobile: cartões entram com translateY(20px→0) + fade-in. Sem translateX lateral.
- *Reduced-motion*: tudo aparece estático com opacity 0→1.

---

### SEÇÃO "COMO FUNCIONA" (fundo Paper)

**Título**: Archivo 900 uppercase: "COMO FUNCIONA"
**Grid "+"**: mesmo padrão da anatomia.

3 blocos, contador "01 / 03" com barra de progresso fina Ink:

**01 — COLE O LINK** (Plex Mono 700 Forest 48px)
"Manda o link do Mercado Livre pro bot no Telegram. Define quanto quer pagar."

**02 — A GENTE VIGIA**
"Coleta automática a cada hora. Na Black Friday, a cada 15 minutos. Sem você fazer nada."

**03 — RECEBE O VEREDITO**
"Quando o preço mudar, você recebe: pode ir, segura, ou monitorando. Com dados, não achismo."

**CTA**: [pendente decisão]
**Reforço**: [pendente decisão — "Leva 30 segundos" depende do modelo]

**Animação**: barra avança por bloco; números fade-in + translateY(-20px). *Reduced-motion*: estático.
**Mobile**: blocos empilhados, barra vertical à esquerda em vez de horizontal.

---

### SEÇÃO "VEREDITO, NÃO ACHISMO" (fundo White)

**Título**: Archivo 900 uppercase: "VEREDITO, NÃO ACHISMO"

3 cards empilhados (mobile) / lado a lado (desktop):

**PODE IR** — borda esquerda Forest 4px, selo Plex Mono 700 fundo Forest texto Paper:
"Preço caiu de verdade, abaixo do normal dos últimos 30 dias. O desconto é real."

**SEGURA** — borda esquerda Ochre 4px, selo fundo Ochre:
"O preço subiu antes de 'cair', ou o preço original é inflado. Desconto maquiado."

**MONITORANDO** — borda esquerda Ink 4px, selo fundo Ink:
"Ainda sem dados suficientes pra afirmar. O alvo é seu — a decisão também."

**Animação**: cards stagger translateY(30px) + fade-in, 0.15s delay. *Reduced-motion*: estático.

---

### SEÇÃO FAQ (fundo Paper)

**Título**: Archivo 900 uppercase: "O QUE TODO MUNDO PERGUNTA"

Accordion, pergunta em Libre Franklin 600, resposta em Libre Franklin 400. Ícone "+" → "×" (rotate 45°, 0.2s).

**"Por que só Mercado Livre?"**
"Porque o ML tem uma API oficial de catálogo com preços públicos. Amazon entra na Fase 2, quando a API de afiliados estiver ativa. Não fazemos scraping — o projeto é público e respeita os Termos de Desenvolvedores."

**"Tem comissão nos links?"**
"Hoje, não. Na Fase 2 (Amazon), os botões 'Ver oferta' vão ter links de afiliado. Mas a comissão nunca influencia o veredito. 'Segura' é segura, mesmo que a gente ganhe se você comprar."

**"Como vocês sabem que o desconto é falso?"**
"Dois testes automáticos (`compute_verdict` em `lowpoint/verdict.py`):
1. **Markup recente**: pegamos o pico de preço dos últimos 14 dias e comparamos com a mediana de todos os preços anteriores a essa janela. Se o pico subiu mais de 10%, o desconto é maquiado — subiram pra baixar.
2. **Preço 'de' inflado**: se o preço riscado do anúncio (original_price) é mais de 10% acima da mediana dos últimos 30 dias, o desconto anunciado é exagerado.
Se nenhum dos dois aciona e o preço caiu pelo menos 5% abaixo da mediana e é o menor já visto, o desconto é real."

**"E se o preço vier de um golpe?"**
"Ofertas abaixo de 60% da mediana das ofertas da coleta são excluídas automaticamente (`select_best_offer` em `lowpoint/best_offer.py`). O alerta avisa quantas foram ignoradas e mostra o menor preço suspeito."

**"É de graça?"**
"Sim. Sem plano pago, sem freemium, sem pegadinha."

**[Pergunta sobre conta/cadastro]**: [pendente decisão web aberta vs. vitrine]

**"É legal coletar esses dados?"**
"Usamos só a API oficial de catálogo do Mercado Livre (`/products/{id}/items`) e seguimos os Termos de Desenvolvedores. Sem scraping, sem dados privados. Código aberto no GitHub."

---

### CTA FINAL (fundo White)

**Título** (Archivo 900):
"O PRÓXIMO DESCONTO VAI VIR.
A PERGUNTA É SE ELE É DE VERDADE."

**CTA**: [pendente decisão]
**Reforço**: [pendente decisão]

**Animação**: título fade-in. *Reduced-motion*: estático.

---

### FOOTER (Ink)
- "LOWPOINT." logo
- Links: "GitHub" · "Como funciona" · "Perguntas"
- Linha Muted: "Dados públicos do Mercado Livre. Sem vínculo com o Mercado Livre. Código aberto."
