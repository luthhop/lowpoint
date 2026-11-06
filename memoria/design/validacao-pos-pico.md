# Validação de descontos pós-pico — 2026-11-05

[TESTE] Simulação em memória; sem rede, banco ou envio ao Telegram.

Preço normal R$ 3.450; pico R$ 6.000; alvo R$ 3.500; os três cenários incluem preço riscado inflado de R$ 6.000 e a amostra atual no histórico, como no coletor.

- Até 3% de desconto sobre o pré-pico: maquiado (inclui exatamente 3%).
- Mais de 3%: aplica regra normal sobre baseline limpo. 4% é neutro; 10% e 20% são reais porque também são mínimos históricos.
- Neutro só envia alerta quando atinge o alvo. Sem alvo atingido, permanece monitorando sem envio.
- Preço riscado inflado não transforma a recuperação pós-pico em SEGURA. Sem pico, permanece a regra existente de original inflado.

Reproduzir: `python scripts/preview_recovered_hike.py`.
Testes: `python -m pytest -q` — 208 passaram; quatro avisos de API legada do SQLAlchemy no webhook.
Regressões: 46 casos em `tests/test_landing_story.py`, incluindo 2,99%, 3%, 3,01%, 4%, 5%, 10%, 20%, alvo atingido/não atingido, preço riscado presente/ausente, baseline contaminado e mínimo histórico anterior.

## Texto final dos três cenários

```text
[TESTE] 4% abaixo do pré-pico | neutro | target_hit
🎯 PS5 Digital Edition bateu teu alvo: R$ 3.312,00.

O alvo foi atingido, mas ainda não reúne os critérios de desconto real.
Preço normal: R$ 3.450,00
Inflaram antes, mas mesmo assim tá 4% abaixo do preço normal.

Loja oficial · Com garantia

[TESTE] 10% abaixo do pré-pico | real | target_hit
✅ PODE IR · PS5 Digital Edition · R$ 3.105,00

Bateu teu alvo de R$ 3.500,00. Esse é de verdade. Pode ir.
Menor preço desde que começamos a monitorar, 10% abaixo do normal.
Inflaram antes, mas mesmo assim tá 10% abaixo do preço normal.

Preço normal: R$ 3.450,00

Loja oficial · Com garantia

[TESTE] 20% abaixo do pré-pico | real | target_hit
✅ PODE IR · PS5 Digital Edition · R$ 2.760,00

Bateu teu alvo de R$ 3.500,00. Esse é de verdade. Pode ir.
Menor preço desde que começamos a monitorar, 20% abaixo do normal.
Inflaram antes, mas mesmo assim tá 20% abaixo do preço normal.

Preço normal: R$ 3.450,00

Loja oficial · Com garantia
```
