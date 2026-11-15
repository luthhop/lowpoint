# Pré-registro — "Os descontos da Black Friday eram reais?"

**Status:** CONGELADO em 15/11/2026 (v1). A versão congelada é o commit marcado pela tag git `pre-registro-v1`.
**Código das regras:** commit `65ed7ef` (HEAD no congelamento). O commit da tag só adiciona documentos em `memoria/`, sem mudar código.
**Mudanças:** só pela seção "Emendas" no fim, com data e motivo. O texto original não é apagado nem reescrito.
**Fonte:** Neon, tabelas `offer_snapshots` (todas as ofertas de cada coleta) e `price_history` (melhor oferta). Só leitura.

## Amostra

20 produtos com watch ativo, todos do Mercado Livre (catálogo `/p/MLB…`):
- 3 pessoais (watches 2, 4, 5: PS5, LG 27", AOC 27"). Histórico desde 02/11 (watch 2) e 09/11 (4 e 5).
- 17 de análise (watches 6–22, lista em `memoria/analise-bf.md`), histórico desde 14/11 ~14:53 BRT. Silenciosos.
- Controles: Pilha Duracell AA (watch 21) e Livro O Alquimista (watch 22). Ficam dentro dos 20, mas P1–P4 também saem com o recorte "18 sem controle".
- Watch 1 (LG 32", inativo desde 09/11) fica **fora**, mesmo que volte a ser ativado.

## Definições comuns

- **Preço do produto numa coleta** = `price_history.price` com `available = true` (melhor oferta nova, sem suspeitas). Coleta com `available = false` é descartada.
- **Horário**: tudo em America/Sao_Paulo. Janelas são semiabertas: [início, fim).
- **Janelas** (fixas, sem sobreposição, iguais para os 20 produtos):
  - **B0**: 14/11 14:50 → 17/11 14:50.
  - **Pré-BF**: 17/11 14:50 → 23/11 00:00 (inclui 22/11 23:59).
  - **BF**: 23/11 00:00 → 28/11 00:00 (inclui 27/11 23:59).
  - **Pós-BF**: 28/11 00:00 → 08/12 00:00 (inclui 07/12 23:59).
- **Referência** `Ref` = mediana dos preços do produto na B0. É o único "preço normal" da análise (P1b, P2, P3, P5).
- **Mínimo de uma janela** = menor preço do produto entre as coletas da janela.
- **Limiares**: os do `lowpoint/config.py` no commit `65ed7ef` (desconto real 5%, pico 10%, fachada 3%, recuo do pico 5%, riscado inflado 1,10×). Não são reajustados depois de ver os dados.
- **Cobertura mínima**: um produto entra numa pergunta só se tiver ≥ 70% das coletas esperadas em cada janela usada (≈ 1/h fora da BF, ≈ 4/h na BF). Se não tiver, aparece como "dados insuficientes" e não é descartado em silêncio.

## P1 — Quantos tiveram desconto real na semana da BF?

Duas respostas, lado a lado. **Se P1a e P1b divergirem, a divergência é um resultado a reportar (com os produtos e o motivo), não um erro a esconder ou corrigir.**

### P1a — O que o Lowpoint teria dito
- **Métrica**: replay offline de `compute_verdict` (commit `65ed7ef`) em cada coleta da BF, usando só o histórico disponível até aquele momento (o mesmo que o coletor teria visto). Nenhum alerta é enviado e nada é gravado.
- **Conta**: veredito `real` em **≥ 2 coletas consecutivas** dentro da BF. Sensibilidade: também reporto com ≥ 1 coleta.
- **Ressalva**: `_detect_hike` só funciona com dado anterior à janela de 14 dias. Para os 17 de análise isso só começa em ~28/11 14:53. **Durante a BF inteira o Lowpoint não consegue marcar "subiu antes" nesses 17**: valem só "≥ 5% abaixo da mediana e menor preço do histórico" + a regra do riscado inflado. P1a reporta isso como é, porque é o que o produto faria.

### P1b — O que a régua fixa diz
- **Métrica**: melhor oferta da BF ≥ 5% abaixo da `Ref` (`preço ≤ Ref × 0,95`).
- **Conta**: em **≥ 2 coletas consecutivas** dentro da BF. Sensibilidade: ≥ 1 coleta.

### Para as duas
- **Resultado**: N de 20 e N de 18 sem controles, com a lista e o maior desconto de cada produto (P1a vs. `baseline_price`; P1b vs. `Ref`).
- **Manchete** (vale para cada uma): "a maioria teve" se ≥ 10 de 18; "não teve" se ≤ 4 de 18; entre isso, "uma minoria teve".

## P2 — Quantos mostraram padrão de maquiagem (subida antes da BF e "queda" na BF)?

Métrica própria da análise, com os limiares do veredito, sobre a `Ref`:
- **Subida**: máximo da Pré-BF ≥ `Ref × 1,10`.
- **"Queda"**: mínimo da BF ≤ `máximo da Pré-BF × 0,95` (recuo ≥ 5% do topo).
- **Fachada**: esse mínimo da BF ≥ `Ref × 0,97` (não ficou mais de 3% abaixo da referência).
- **Conta como maquiagem**: as três condições ao mesmo tempo. Subida + queda que vai abaixo de `Ref × 0,97` conta como "subiu antes, mas o desconto foi real" (reportado à parte).
- **Resposta**: contagem de 20 e de 18. "Sim, houve maquiagem" se ≥ 1 produto (documentado caso a caso, com gráfico); a manchete "foi comum" só se ≥ 5 de 18.

## P3 — O preço riscado anunciado é honesto?

- **Unidade principal**: a melhor oferta (o que o Lowpoint mostra), em cada coleta da BF que tenha `original_price`.
- **Métrica**: razão `original_price / Ref`. Inflado se > 1,10 (mesma regra `INFLATED_ORIGINAL_THRESHOLD`).
- **Por produto**: "riscado inflado" se a razão passa de 1,10 em > 50% das coletas da BF com riscado. Produto sem riscado na BF = "sem riscado" (fora do denominador).
- **Secundária (por anúncio)**: em `offer_snapshots`, para cada `item_id` que também apareceu na B0, razão `original_price na BF / mediana do preço do próprio item na B0`. Responde "o vendedor já cobrou esse preço riscado?".
- **Resposta**: "não é honesto" se ≥ 50% dos produtos com riscado tiveram riscado inflado; "é honesto" se ≤ 20%; entre isso, "depende do produto". Sempre com o denominador explícito.

## P4 — O menor preço do período caiu na BF ou depois (até 07/12)?

- **Métrica**: mínimos de B0 + Pré-BF (14/11–22/11, juntas como "antes"), BF e Pós-BF por produto.
- **Classificação**: a janela com o menor mínimo ganha se for pelo menos 1% menor que o segundo menor. Diferença < 1% = "empate" (reportado como tal).
- **Resposta**: "sim, a BF foi o melhor momento" se a BF ganhar em ≥ 50% dos 18 sem controle; "não, valeu esperar" se o Pós-BF ganhar em ≥ 50%; senão, "sem padrão".
- Também reporto quanto o mínimo do Pós-BF ficou abaixo/acima do mínimo da BF (mediana dos 18).

## P5 — Os controles (pilha, livro) se comportaram diferente?

Com 2 controles é descritivo, sem teste estatístico.
- **Métricas por produto**: (a) variação da mediana da BF vs. `Ref`; (b) amplitude `(máx − mín) / Ref` no período todo; (c) resultado em P1a, P1b e P2.
- **Esperado dos controles**: |variação BF vs. Ref| < 5%, nenhum desconto real em P1a e P1b, nenhuma maquiagem em P2.
- **"Sim, se comportaram diferente"**: os 2 controles dentro do esperado **e** a mediana de |variação BF vs. Ref| dos 18 ≥ 5%. "Não": algum controle fora do esperado, ou os 18 também ficaram parados (< 5%). Se só um controle sair do esperado: "misto", com a explicação.

## Limitações conhecidas

- **Histórico curto**: 17 dos 20 começam em 14/11. Se o preço já tinha subido antes disso, essa subida vira a `Ref` e a maquiagem fica invisível. A análise só enxerga subidas a partir de 14/11.
- **A B0 pode já estar inflada**: campanhas de novembro começam cedo, e 14–17/11 já é novembro. Uma `Ref` inflada faz descontos parecerem maiores em P1b e esconde maquiagem em P2.
- **Produtos com histórico mais longo**: PS5 (desde 02/11) e os dois monitores (desde 09/11). Uma sensibilidade com referência mais longa para esses 3 fica como **exploratória** e não muda as respostas.
- **Detector de pico do Lowpoint cego na BF** para os 17 (ver P1a). P1a e P2 usam métricas diferentes, e um produto pode estar em P2 sem aparecer como SEGURA em P1a.
- **Poucos vendedores**: TV TCL 55 C6K (watch 7, ~1,2 oferta/coleta, 3 vendedores no total) e iPhone 17 256GB (watch 13, ~3 ofertas, 2 vendedores). O preço deles é o de 1–2 lojas, não de um mercado.
- **Um único site**: só Mercado Livre, só anúncios de catálogo.
- **Amostra pequena e não aleatória**: 20 produtos escolhidos à mão (3 por interesse pessoal). O resultado descreve esses 20, não "a Black Friday brasileira".
- **Preço medido ≠ preço pago**: sem cupom, Pix, parcelamento, Meli+ ou cashback. Frete gravado só como "grátis sim/não".
- **Resolução**: 1 coleta/h fora da BF (15 min na BF). Uma oferta relâmpago menor que isso pode passar despercebida.
- **Riscado**: o coletor usa `sale_price.amount`/`regular_amount` só quando a resposta traz `sale_price`; senão, `price`/`original_price` do anúncio. Na resposta real de 15/11 não existe `sale_price`, então o gravado é `price` e `original_price` (conferido: 32/32 ofertas do DualSense batem no centavo com o snapshot das 08:45). Não se sabe se quem define esse valor é o ML ou o vendedor. No DualSense, só 1 das 32 ofertas tinha riscado.

## Coleta

- **Manter a coleta dos 20 até 07/12 23:59** sem desativar nenhum watch (`collect_once` só coleta watches ativos). O dataset é cortado em 08/12 00:00; o que vier depois não muda nenhuma resposta.
- Ritmo atual mantido: horária fora da BF, 15 min em 23–27/11 (tick).
- Antes de rodar a análise: `scripts/audit_collections.py` sobre o período, e a cobertura de cada produto vai junto no resultado.

## O que NÃO muda depois do congelamento (15/11)

- Perguntas, métricas, janelas e limiares deste documento.
- A lista de 20 produtos e os 2 controles (sem trocar, tirar ou adicionar; produto novo não entra).
- O commit das regras usado no replay de P1a (`65ed7ef`). Se o veredito mudar em produção, a análise continua com o commit congelado e a mudança é citada no texto.
- As regras de seleção da melhor oferta e de suspeitas (60% da mediana) usadas para montar o preço do produto.
- Análise extra feita depois de ver os dados é marcada como **exploratória**, separada das respostas P1–P5.

## Anexo — campos da API que o coletor não grava (15/11, só registro)

Uma chamada READ ONLY a `/products/MLB28083897/items` (DualSense), HTTP 200, 32 ofertas. Nenhuma proposta de gravação aqui.
- **Ligados a promoção/campanha**: `deal_ids` (presente, vazio nas 32), `tags` do anúncio (`standard_price_by_channel`, `standard_price_by_quantity`, `net_proceeds_prices` em 1–2 ofertas), `experiments` no topo da resposta (null).
- **Frete**: `shipping.cost`, `shipping.logistic_type`, `shipping.tags` (ex.: `mandatory_free_shipping`), `shipping.mode`, `local_pick_up`, `store_pick_up`.
- **Anúncio**: `listing_type_id` (`gold_special`/`gold_pro`), `category_id`, `user_product_id`, `inventory_id`, `tier`, `min_purchase_unit`, `accepts_mercadopago`, `international_delivery_mode`, `currency_id`, `site_id`.
- **Vendedor**: `seller_address` (cidade, bairro, estado).
- **Garantia estruturada**: `sale_terms` (`WARRANTY_TYPE`, `WARRANTY_TIME`); hoje gravamos só o texto de `warranty`.

## Dados exploratórios

- `deal_ids` e `tags` dos anúncios passam a ser gravados a partir da data em que essa mudança entrar no ar. A data do deploy é anotada aqui como emenda.
- Antes dessa data não existem; nenhum valor é reconstruído para trás.
- São usados **só em análise exploratória** (ex.: "anúncios com deal na BF tiveram mais desconto real?") e **não alteram P1–P5**: nem métricas, nem janelas, nem quais produtos ou coletas entram.

## Emendas

Formato: `### Emenda N — dd/mm/aaaa` + o que mudou + motivo + se afeta alguma resposta já calculada.

### Emenda 1 — 15/11/2026

- **O que mudou**: `offer_snapshots` passou a gravar `deal_ids` e `tags` de cada anúncio (seção "Dados exploratórios"). Commit da mudança: `7da404c` (migração `a6b7c8d9e0f1`, aplicada no Neon às 09:36).
- **Primeira coleta com os campos**: 15/11/2026 09:45:29 BRT (20 produtos, 527 ofertas; deal_ids: 526 `[]` e 1 preenchido; tags preenchidas nas 527). As 22.296 linhas anteriores ficam com NULL.
- **Motivo**: permitir análise exploratória de campanhas/deals na BF.
- **Efeito**: **não altera P1–P5** (métricas, janelas, limiares, produtos e coletas usadas continuam as da v1).

### Emenda 2 — 15/11/2026 10:18 BRT

- **Motivo**: esclarecer critérios antes de qualquer dado da BF (só a B0 está em andamento; nenhuma resposta de P1–P5 foi calculada). **Não muda janelas, limiares do veredito nem o commit das regras.**
- **P5** (o texto da v1 era contraditório entre "algum controle fora → não" e "só um fora → misto"): se a mediana de |variação BF vs. Ref| dos 18 for < 5% ("os 18 parados"), a resposta é "não". Senão: 2 controles no esperado → "sim"; 1 → "misto"; 0 → "não". P5 só é respondida com os 2 controles com cobertura.
- **Cobertura** (substitui "não é descartado em silêncio" como regra de manchete):
  - Produto com cobertura < 70% numa janela usada pela pergunta é **excluído daquela pergunta** (não das outras) e não anula a pergunta. O relatório lista os excluídos e o motivo.
  - Os cortes de manchete viram **proporção dos produtos com cobertura** entre os 18 não-controle: P1a/P1b "a maioria" ≥ 10/18 (≈ 55,6%), "não teve" ≤ 4/18 (≈ 22,2%); P2 "foi comum" ≥ 5/18 (≈ 27,8%); P3 e P4 já eram proporções (50% / 20%, 50%). Comparação com a fração exata, para 10 de 18 continuar sendo "a maioria".
  - A manchete só é calculada com **≥ 12 dos 18** cobertos; abaixo disso, "incompleto".
- **P3**: a base é a mesma dos 18 não-controle (denominador: os que tiveram riscado na BF). Os controles ficam no P5.
- **Efeito**: nenhuma resposta já calculada (não havia nenhuma).
