# Painel ao vivo da vitrine — especificação (proposta)

**Status:** PROPOSTA para revisão do Lucas · 15/11/2026 · sem código. Decisão de origem: "Versão web (2026-11-14)" em `memoria/decisoes.md` (vitrine com dados ao vivo, só leitura).
**Fluxo:** a /ao-vivo foi feita direto no código, seguindo a marca, por ser uma tela de dados; revisão visual no Paper fica opcional (decisão de 15/11).

## 1. Endpoint público só leitura

### Onde: projeto `lowpoint` (o do bot), em `GET /api/painel`

- **Por quê no bot e não no `lowpoint-web`:**
  - O `lowpoint` já roda Python na Vercel e já tem `DATABASE_URL` com o Neon. O `lowpoint-web` é estático (Vite) e não tem nenhum segredo. Manter assim é a menor superfície: nada de credencial de banco no projeto do site.
  - Reaproveita o código existente: `lowpoint.db`, e a Referência calculada com `analysis.prereg` + `analysis.metrics.reference` (só biblioteca padrão, sem pandas). É o mesmo número que a análise de dezembro vai usar.
- **Custo de estar no bot:** um deploy do painel também redeploya o webhook e o tick. Mitigação: arquivo próprio (`api/painel.py`), sem tocar em `webhook.py`/`tick.py`, com testes antes do deploy. O `vercel.json` (formato `builds` + `routes`) precisa de uma entrada nova para ele.
- **Como o site consome:** `fetch` direto de `https://lowpoint-theta.vercel.app/api/painel` (projeto `lowpoint`; configuração em `frontend/README.md`, seção "Vitrine /ao-vivo"), com `Access-Control-Allow-Origin: https://lowpoint-web.vercel.app` (uma origem só, só `GET`). Alternativa: rewrite no `lowpoint-web` de `/api/painel` para o `lowpoint`, deixando tudo na mesma origem; isso só vale se o rewrite externo respeitar o cache (conferir na implementação).

### Contrato JSON (v1)

Valores monetários como **string decimal** (decisão "nunca float"). Datas em ISO 8601 UTC; a página exibe em America/Sao_Paulo.

```json
{
  "versao": 1,
  "gerado_em": "2026-11-15T13:20:04Z",
  "ultima_coleta": "2026-11-15T12:45:34Z",
  "coleta_atrasada": false,
  "amostragem": "último preço de cada bloco de 3h (horário de Brasília)",
  "referencia": {
    "definicao": "mediana da melhor oferta de 14/11 14:50 a 17/11 14:50",
    "inicio": "2026-11-14T17:50:00Z",
    "fim": "2026-11-17T17:50:00Z",
    "parcial": true
  },
  "produtos": [
    {
      "id": "MLB28083897",
      "nome": "DualSense Cobalt",
      "categoria": "Games",
      "url": "https://www.mercadolivre.com.br/p/MLB28083897",
      "preco_atual": "380.00",
      "preco_atual_em": "2026-11-15T12:45:34Z",
      "disponivel": true,
      "poucas_ofertas": false,
      "referencia": "380.00",
      "vs_referencia_pct": "0.0",
      "faixa": "neutra",
      "serie": [["2026-11-14T18:00:00Z", "380.00"], ["2026-11-14T21:00:00Z", "380.00"]]
    }
  ]
}
```

| Campo | Regra |
|---|---|
| `produtos` | Exatamente os 20 do pré-registro, numa **allowlist fixa no código** (a lista de `analysis.prereg`). Um watch novo nunca aparece sozinho. Ordem fixa por categoria. |
| `id` | catalog_product_id. Já é público: está na URL do ML. |
| `nome` | Nome curto escrito por nós (lista do pré-registro). Nunca `watches.nickname`. |
| `categoria` | As categorias de `memoria/analise-bf.md`. Os 3 produtos pessoais entram numa categoria comum (PS5 → Games; monitores → Celular e computador), para nada separar "os meus". Pilha e livro → "Controle". |
| `preco_atual` | Último `price_history` com `available = true`; `null` (e `preco_atual_em` também) quando `disponivel = false` (Termos ML 5.2, 17/11). |
| `disponivel` | `false` se a coleta mais recente do produto veio com `available = false` (ver Riscos). |
| `poucas_ofertas` | `true` se a coleta mais recente teve < 3 ofertas (mesma regra do rodapé dos alertas). Usa só a contagem, nunca o anúncio nem o vendedor. |
| `referencia` / `parcial` | Mediana da B0, com `parcial: true` até 17/11 14:50 BRT. Sem coletas na B0, vem `null`. |
| `vs_referencia_pct` | `(preço_atual − ref) / ref`, uma casa decimal, **truncado em direção a zero** para nunca exagerar (mesma lógica do floor de 05/11). `null` sem referência ou sem oferta. |
| `faixa` | `abaixo` se ≤ −5,0%; `acima` se ≥ +10,0%; senão `neutra`. É calculada no servidor, para cor e texto saírem da mesma regra. |
| `serie` | Desde 14/11 14:50 (B0) para todos, inclusive os que têm histórico antes disso. Último preço disponível de cada bloco de 3h alinhado a 00/03/06…/21h BRT. "Último" e não "mínimo": o mínimo exageraria quedas relâmpago. Até 08/12 são ~190 pontos por produto. Lista vazia quando `disponivel = false` (Termos ML 5.2, 17/11). |

**Nunca expor** (o servidor monta o JSON campo a campo, sem serializar modelo): alvo (`target_price`), `chat_id`, `seller_id`, `item_id`, `silent`, `nickname`, `group`/"pessoal", `watch_id`, alertas, tokens. Um teste compara as chaves do JSON com uma lista permitida e procura os nomes proibidos no corpo.

### Consulta ao Neon

- Uma requisição sem cache faz **uma ida ao banco**, numa transação READ ONLY:
  - uma consulta `DISTINCT ON (product_id, bloco)` em `price_history` (usa o índice `ix_price_history_product_collected`);
  - `max(collected_at)` e contagem de ofertas da última coleta em `offer_snapshots`.
- Volume: ~20 × 936 linhas até 08/12 no pior caso, reduzidas no próprio SQL.

### Cache

```
Cache-Control: public, max-age=300, s-maxage=3600, stale-while-revalidate=3600
```

- A CDN da Vercel guarda 1h; depois disso, serve a versão antiga enquanto revalida **uma vez** em segundo plano. O navegador guarda 5 min.
- **Consultas por dia:** no máximo 1 por hora por região da CDN com tráfego, ou seja **≤ 24/dia** se o público for só do Brasil (uma região), ≤ 48 com duas. Sem visitas, 0. Para comparar: o coletor já faz centenas de consultas por dia (20 produtos × 24 execuções × várias consultas cada).
- **Compute do Neon:** cada revalidação fora da hora da coleta pode acordar o banco (fica ligado ~5 min). Pior caso: +24 acordadas/dia. Otimização opcional: calcular o `s-maxage` para expirar logo depois da coleta das :45 (por volta das :48), quando o banco ainda está acordado. Assim a maioria das revalidações não acorda nada.
- Na BF a coleta é a cada 15 min, mas o painel continua com cache de 1h: com blocos de 3h, mais frescor não muda o gráfico.

### Proteção mínima (sem autenticação)

- **Ataque de cache-busting:** a CDN usa a URL inteira como chave, então `?x=1`, `?x=2`… furariam o cache e acertariam o Neon a cada pedido. O endpoint responde **400 sem tocar no banco** se vier qualquer query string, e só aceita `GET`/`HEAD`.
- **Memo na instância:** com Fluid Compute a instância é reaproveitada; um cache em memória de 1h dentro da função evita repetir a consulta entre regiões que caiam na mesma instância.
- **Rate limit:** desnecessário de início, porque o cache absorve o tráfego. Se aparecer abuso, uma regra de rate limit no Firewall da Vercel só para `/api/painel`, sem código.
- **Erro do banco:** responde 503 com `Cache-Control: no-store`, para não envenenar o cache. Na implementação, conferir se a CDN continua servindo a versão antiga quando a revalidação falha.

## 2. O que a página mostra (texto do wireframe)

### Onde entra: **página própria `/ao-vivo`**, com um bloco-chamada na landing

- **Por quê página e não seção:**
  - A landing conta uma história com dados **ilustrativos** (`demo-history.json`, `illustrative: true`). Misturar com preços reais na mesma rolagem confunde o que é exemplo e o que é medido.
  - A landing continua estática e rápida, e não quebra se o endpoint cair.
  - `/ao-vivo` é um link próprio para compartilhar durante a BF.
  - No Vite dá para fazer como segunda página (multi-page), sem adicionar roteador.
- **Na landing:** um bloco curto antes do FAQ: "Os preços reais, agora. Ver a vitrine ao vivo →".
- **Conflitos no wireframe v11 que precisam mudar** (texto proposto, aprovação no Paper):
  - O subtítulo do HERO promete "…e o veredito de cada preço". Proposta: "Veja ao vivo os preços que o Lowpoint está vigiando. O bot no Telegram está em beta fechado, por convite."
  - O reforço do CTA FINAL diz "os preços ao vivo estão logo acima". Proposta: "Ou só olha a vitrine ao vivo." com link para `/ao-vivo`.

### Estrutura da página

1. **Cabeçalho:** "AO VIVO" (Archivo 900) + "20 produtos que o Lowpoint está vigiando, atualizados de hora em hora." Abaixo, em Plex Mono Muted: "Última coleta: 15/11, 09:45 · atualiza de hora em hora (a cada 15 min de 23 a 27/11)." (de `ultima_coleta`).
2. **Uma linha de aviso, sempre visível:** "Sem veredito ao vivo: o detector de pico precisa de 14 dias de histórico, e o veredito oficial sai na análise de dezembro."
3. **Grade de 20 cartões (small multiples)**, agrupados por categoria (título pequeno da categoria acima de cada grupo). Cada cartão tem:
   - nome (Libre Franklin 600) e link discreto "ver anúncio";
   - mini-gráfico em degraus (série de 3h), linha Ink, linha da Referência tracejada em Muted e a faixa da BF levemente marcada com o rótulo "BF" (Plex Mono 9px, #666, no topo; 12px reservados no alto da escala para nenhuma linha passar por cima), **com o mesmo eixo de tempo em todos os cartões** (14/11 → 28/11 00:00 até a BF acabar; depois 14/11 → 08/12) e o eixo de preço próprio de cada produto;
   - preço atual (Plex Mono 700);
   - "−7,2% vs referência" (Plex Mono 500), sempre com sinal e com palavra, não só cor;
   - até 17/11 14:50 (Referência parcial), "referência fecha em 17/11" no lugar do percentual;
   - estados especiais: "indisponível agora" e "poucos vendedores" (ver Riscos).
4. **Nota de método** (rodapé, 3–4 linhas): "Preço = melhor oferta nova do catálogo, coletada de hora em hora (a cada 15 min de 23 a 27/11) e mostrada em blocos de 3h. Referência = mediana de 14/11 14:50 a 17/11 14:50. As regras da análise foram registradas antes da Black Friday: [pré-registro v1](https://github.com/luthhop/lowpoint/blob/pre-registro-v1/memoria/analise/plano-pre-registro.md) · [emendas](https://github.com/luthhop/lowpoint/blob/main/memoria/analise/plano-pre-registro.md#emendas)."
   - O link da tag mostra o texto congelado **sem** as Emendas 1 e 2, por isso o segundo link aponta para o `main`.

### Cores

| Situação | Cor | Texto |
|---|---|---|
| ≥ 5% abaixo da Referência (`faixa: abaixo`) | Forest #1B6B3A | "−X% vs referência" |
| ≥ 10% acima (`faixa: acima`) | Ochre #7A5A10 | "+X% vs referência" |
| Entre os dois | Ink #0A0A0A | "±X% vs referência" |
| Metadados, "referência fecha em", sem oferta | Muted #666666 (texto); #999999 só em linhas | — |

**Tensão com a marca, para você decidir:** as decisões atuais dizem "Forest só para desconto **verificado como real**" e "Ochre só para veredito **segura**". Aqui, Forest marca só "≥ 5% abaixo da referência", sem a condição de menor preço do histórico, e Ochre marca "≥ 10% acima", que não é veredito. Como mitigação, os textos nunca dizem "desconto real", "pode ir" nem "segura", só "vs referência", e a linha de aviso explica. Se aprovar assim, isso vira uma decisão nova (exceção da vitrine) em `decisoes.md`.

## 3. Riscos

- **Custo no Neon:** limitado pelo cache (≤ 24–48 consultas/dia), pelo bloqueio de query string e pelo memo na instância. O ponto de atenção é o compute (acordar o banco), não o armazenamento. Conferir as horas de compute no painel do Neon na primeira semana. Se ficar caro, o plano B é o coletor gerar o JSON a cada coleta e publicar como arquivo estático, com zero leitura do banco pela web.
- **Coleta falhou:** a página mostra sempre "Última coleta: dd/mm, hh:mm". Se `ultima_coleta` tiver mais de 90 min (o mesmo limite do aviso de atraso do tick), `coleta_atrasada: true` e aparece a linha "A coleta está atrasada; os preços abaixo são de dd/mm, hh:mm." Nunca dar a entender que o dado é fresco. Se o endpoint falhar: "Não deu para carregar os preços agora." Sem dado inventado e sem cache local antigo apresentado como atual.
- **Produto sem oferta** (Termos ML 5.2, 17/11): se a última coleta veio `available = false`, o cartão mostra só o nome, "indisponível agora" e o link "ver anúncio": sem valor, sem percentual e sem mini-gráfico. A API devolve `preco_atual`, `preco_atual_em` e `vs_referencia_pct` como `null`. Com < 3 ofertas aparece "poucos vendedores", como no bot.
- **Mobile:** 20 cartões numa coluna dão uma rolagem longa. Proposta: 2 colunas a partir de 360px, cartão compacto (mini-gráfico ~140×44px, preço e %), sem rótulos de eixo no mini-gráfico (a nota de método explica a escala). Desktop: 4 colunas. Payload: ~3.800 pontos, ~120 KB de JSON cru, ~25 KB com gzip. Dá para encurtar (epoch em segundos) se pesar.
- **Leitura como veredito:** a cor e o "% vs referência" podem ser lidos como "promoção boa". Mitigação: a linha de aviso fixa e a ausência de palavras de veredito.
- **Privacidade:** a allowlist de 20 impede que um watch pessoal novo apareça. Os 3 pessoais ficam indistinguíveis (categoria comum, sem "grupo"). O teste de chaves proibidas roda a cada deploy.
- **Termos do ML:** conferir nos Termos de Desenvolvedores se a exibição pública de preços vindos da API tem alguma restrição. A landing já mostra o chip "Dados públicos do ML".
- **Regressão no bot:** o endpoint mora no projeto do webhook. Arquivo e rota separados, com testes antes do deploy, e o deploy fora da janela :40–:50.
