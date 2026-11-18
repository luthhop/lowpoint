"""Parser do /adicionar <link> [alvo] [apelido].

Depois do link, o próximo token é o alvo se for um preço válido; o resto é
apelido. Se não for preço, tudo vira apelido e o watch fica sem alvo.
"""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

# 3.500 | 3.500,00 | 1.250.000 (ponto de milhar, vírgula decimal)
_THOUSANDS = re.compile(r"\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?")
# 3500 | 3500,00 | 99,9
_COMMA_DECIMAL = re.compile(r"\d+(?:,\d{1,2})?")
# 3500.50 (formato que o /adicionar já aceitava)
_DOT_DECIMAL = re.compile(r"\d+\.\d{1,2}")
_CURRENCY = re.compile(r"^r\$", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedAdicionar:
    url: str | None
    target: Decimal | None
    nickname: str | None


def parse_price(token: str) -> Decimal | None:
    """Preço em formato brasileiro (aceita "R$" colado). None se não for preço > 0."""
    t = _CURRENCY.sub("", token.strip())
    if _THOUSANDS.fullmatch(t):
        t = t.replace(".", "").replace(",", ".")
    elif _COMMA_DECIMAL.fullmatch(t):
        t = t.replace(",", ".")
    elif not _DOT_DECIMAL.fullmatch(t):
        return None
    try:
        value = Decimal(t)
    except InvalidOperation:
        return None
    return value if value > 0 else None


def parse_adicionar(text: str) -> ParsedAdicionar:
    parts = text.split(maxsplit=1)
    rest = parts[1].strip() if len(parts) > 1 else ""
    if not rest:
        return ParsedAdicionar(None, None, None)

    url, _, rest = rest.partition(" ")
    rest = rest.strip()
    target = None

    if rest:
        first, _, after = rest.partition(" ")
        candidate, remainder = first, after
        if first.lower() == "r$" and after.strip():
            # "R$ 3.500": o símbolo veio separado do número.
            candidate, _, remainder = after.strip().partition(" ")
        price = parse_price(candidate)
        if price is not None:
            target = price
            rest = remainder.strip()

    return ParsedAdicionar(url=url, target=target, nickname=rest or None)
