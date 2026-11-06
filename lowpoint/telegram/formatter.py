import math
from dataclasses import dataclass
from decimal import Decimal
from html import escape

from lowpoint.config import FACHADA_THRESHOLD, MIN_MONITORING_DAYS


def fmt_brl(value: Decimal) -> str:
    s = f"{value:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _dias(n: int) -> str:
    if n == 0:
        return "hoje"
    return "1 dia" if n == 1 else f"{n} dias"


def item_url(item_id: str) -> str:
    prefix = item_id[:3]
    number = item_id[3:]
    return f"https://produto.mercadolivre.com.br/{prefix}-{number}"


def _pct(a: Decimal, b: Decimal) -> str:
    if b == 0:
        return "0%"
    return f"{math.floor(abs((a - b) / b) * 100)}%"


@dataclass(frozen=True)
class AlertContext:
    product_name: str
    item_id: str
    price: Decimal
    original_price: Decimal | None
    target_price: Decimal
    verdict: str
    reason: str
    lowest_price: Decimal | None
    median_30d: Decimal | None
    monitoring_days: int
    pre_hike_price: Decimal | None
    has_warranty: bool
    is_official: bool
    suspect_count: int
    hike_pct: Decimal | None = None
    hike_days: int | None = None
    baseline_price: Decimal | None = None
    cheapest_suspect_price: Decimal | None = None
    offer_count: int = 0


@dataclass(frozen=True)
class AlertMessage:
    text: str
    parse_mode: str
    button_text: str
    button_url: str
    alert_type: str


def _footer(ctx: AlertContext) -> str:
    parts: list[str] = []
    if not ctx.has_warranty:
        parts.append("\n<b>Sem garantia informada</b>")
    details: list[str] = []
    if ctx.is_official:
        details.append("Loja oficial")
    else:
        details.append("Vendedor não oficial")
    if ctx.has_warranty:
        details.append("Com garantia")
    parts.append("\n" + " · ".join(details))
    if ctx.suspect_count > 0 and ctx.cheapest_suspect_price is not None:
        parts.append(
            f"\nIgnorei um anúncio de {fmt_brl(ctx.cheapest_suspect_price)}, "
            f"bem abaixo do normal: costuma ser golpe."
        )
    if 0 < ctx.offer_count < 3:
        parts.append(
            "\nPoucos vendedores agora — confere antes de comprar."
        )
    return "".join(parts)


def _claimed_discount(ctx: AlertContext) -> str | None:
    if ctx.original_price and ctx.original_price > ctx.price:
        pct = _pct(ctx.price, ctx.original_price)
        return f"Preço riscado: {fmt_brl(ctx.original_price)} (−{pct})."
    return None


def _recovered_hike_note(ctx: AlertContext) -> list[str]:
    if (
        ctx.pre_hike_price is not None
        and ctx.pre_hike_price > ctx.price
        and ctx.hike_pct is not None
    ):
        discount = _pct(ctx.price, ctx.pre_hike_price)
        return [
            f"Inflaram antes, mas mesmo assim tá {discount} abaixo do preço normal."
        ]
    return []


def format_alert(ctx: AlertContext) -> AlertMessage:
    target_hit = ctx.price <= ctx.target_price

    if target_hit and ctx.verdict == "maquiado":
        return _format_target_hit_maquiado(ctx)
    if target_hit and ctx.verdict == "real":
        return _format_target_hit_real(ctx)
    if target_hit and ctx.verdict == "neutro":
        return _format_target_hit_neutro(ctx)
    if ctx.verdict == "real":
        return _format_verdict_real(ctx)
    if ctx.verdict == "maquiado":
        return _format_maquiado(ctx)
    return _format_neutro(ctx)


def _format_target_hit_real(ctx: AlertContext) -> AlertMessage:
    name = escape(ctx.product_name)
    normal = ctx.baseline_price or ctx.median_30d
    lines = [f"<b>✅ PODE IR</b> · {name} · <b>{fmt_brl(ctx.price)}</b>"]
    lines.append("")
    lines.append(
        f"Bateu teu alvo de {fmt_brl(ctx.target_price)}. "
        f"Esse é de verdade. Pode ir."
    )
    if normal and normal > 0:
        discount = _pct(ctx.price, normal)
        if ctx.lowest_price is not None and ctx.price <= ctx.lowest_price:
            period = "desde que começamos a monitorar"
        else:
            period = f"em {_dias(ctx.monitoring_days)}"
        lines.append(
            f"Menor preço {period}, "
            f"{discount} abaixo do normal."
        )
    lines.extend(_recovered_hike_note(ctx))
    lines.append("")
    if normal:
        lines.append(f"Preço normal: {fmt_brl(normal)}")
    if ctx.lowest_price and ctx.lowest_price != ctx.price:
        lines.append(f"Menor anterior: {fmt_brl(ctx.lowest_price)}")
    lines.append(_footer(ctx))
    return AlertMessage(
        text="\n".join(lines),
        parse_mode="HTML",
        button_text="Ver oferta",
        button_url=item_url(ctx.item_id),
        alert_type="target_hit",
    )


def _format_target_hit_neutro(ctx: AlertContext) -> AlertMessage:
    name = escape(ctx.product_name)
    since = "desde hoje" if ctx.monitoring_days == 0 else f"há {_dias(ctx.monitoring_days)}"
    lines = [
        f"🎯 <b>{name}</b> bateu teu alvo: <b>{fmt_brl(ctx.price)}</b>.",
        "",
    ]
    if ctx.monitoring_days < MIN_MONITORING_DAYS:
        lines.append(
            f"Ainda tô conhecendo esse produto (monitorando {since}), "
            f"então não dá pra dizer se o desconto é de verdade. O alvo é teu."
        )
    else:
        lines.append("O alvo foi atingido, mas ainda não reúne os critérios de desconto real.")
        normal = ctx.baseline_price or ctx.median_30d
        if normal:
            lines.append(f"Preço normal: {fmt_brl(normal)}")
    lines.extend(_recovered_hike_note(ctx))
    lines.append(_footer(ctx))
    return AlertMessage(
        text="\n".join(lines),
        parse_mode="HTML",
        button_text="Ver oferta",
        button_url=item_url(ctx.item_id),
        alert_type="target_hit",
    )


def _format_verdict_real(ctx: AlertContext) -> AlertMessage:
    name = escape(ctx.product_name)
    normal = ctx.baseline_price or ctx.median_30d
    lines = [f"<b>✅ PODE IR</b> · {name} · <b>{fmt_brl(ctx.price)}</b>"]
    lines.append("")
    if normal and normal > 0:
        discount = _pct(ctx.price, normal)
        lines.append(
            f"Novo menor preço, {discount} abaixo do normal. "
            f"Esse é de verdade. Pode ir."
        )
    else:
        lines.append("Novo menor preço. Esse é de verdade. Pode ir.")
    lines.extend(_recovered_hike_note(ctx))
    lines.append("")
    if normal:
        lines.append(f"Preço normal: {fmt_brl(normal)}")
    if ctx.lowest_price and ctx.lowest_price != ctx.price:
        lines.append(f"Menor anterior: {fmt_brl(ctx.lowest_price)}")
    lines.append(_footer(ctx))
    return AlertMessage(
        text="\n".join(lines),
        parse_mode="HTML",
        button_text="Ver oferta",
        button_url=item_url(ctx.item_id),
        alert_type="verdict_real",
    )


def _format_maquiado(ctx: AlertContext) -> AlertMessage:
    name = escape(ctx.product_name)
    lines = [f"<b>⚠ SEGURA</b> · {name} · <b>{fmt_brl(ctx.price)}</b>"]
    lines.append("")
    claimed = _claimed_discount(ctx)
    if claimed:
        lines.append(claimed)
    if ctx.pre_hike_price and ctx.hike_pct is not None:
        lines.append(f"Antes de subir, custava {fmt_brl(ctx.pre_hike_price)}.")
        hike_str = f"{ctx.hike_pct * 100:.0f}%"
        dias = ctx.hike_days if ctx.hike_days else 14
        diff = ctx.price - ctx.pre_hike_price
        prefix = f"Subiram {hike_str} há {dias} dias e baixaram de volta. "
        if diff > 0:
            lines.append(
                prefix
                + f"Tá {fmt_brl(diff)} mais caro que antes. Segura."
            )
        elif diff < 0:
            pct_below_dec = abs(diff) / ctx.pre_hike_price
            pct_below_str = f"{math.floor(pct_below_dec * 100)}%"
            if pct_below_dec <= FACHADA_THRESHOLD:
                lines.append(
                    prefix
                    + f"Tá só {pct_below_str} abaixo do que custava antes. "
                    f"Desconto de fachada. Segura."
                )
            else:
                lines.append(
                    prefix
                    + f"Tá {pct_below_str} abaixo do que custava antes, "
                    f"mas inflaram antes de baixar. Segura."
                )
        else:
            lines.append(
                prefix
                + "Voltou ao preço de antes. Desconto de fachada. Segura."
            )
    else:
        normal = ctx.baseline_price or ctx.median_30d
        if normal:
            lines.append(f"Preço normal no último mês: {fmt_brl(normal)}.")
        if ctx.pre_hike_price and ctx.pre_hike_price < ctx.price:
            increase = ((ctx.price - ctx.pre_hike_price) / ctx.pre_hike_price) * 100
            lines.append(
                f"Subiram pra baixar. Preço subiu {increase:.0f}% nas 2 semanas "
                f'antes da "queda" (era {fmt_brl(ctx.pre_hike_price)}). Segura.'
            )
        else:
            lines.append("Subiram pra baixar. Segura.")
    lines.append(_footer(ctx))
    return AlertMessage(
        text="\n".join(lines),
        parse_mode="HTML",
        button_text="Ver oferta",
        button_url=item_url(ctx.item_id),
        alert_type="verdict_maquiado",
    )


def _format_target_hit_maquiado(ctx: AlertContext) -> AlertMessage:
    name = escape(ctx.product_name)
    lines = [f"<b>⚠ SEGURA</b> · {name} · <b>{fmt_brl(ctx.price)}</b>"]
    lines.append("")
    lines.append(
        f"Bateu teu alvo de {fmt_brl(ctx.target_price)}, "
        f"mas subiram pra baixar. Segura."
    )
    claimed = _claimed_discount(ctx)
    if claimed:
        lines.append(claimed)
    normal = ctx.baseline_price or ctx.median_30d
    if normal:
        lines.append(f"Preço normal no último mês: {fmt_brl(normal)}.")
    lines.append(_footer(ctx))
    return AlertMessage(
        text="\n".join(lines),
        parse_mode="HTML",
        button_text="Ver oferta",
        button_url=item_url(ctx.item_id),
        alert_type="target_hit_maquiado",
    )


def _format_neutro(ctx: AlertContext) -> AlertMessage:
    name = escape(ctx.product_name)
    lines = [f"<b>MONITORANDO</b> · {name} · <b>{fmt_brl(ctx.price)}</b>"]
    lines.append("")
    lines.append(f"Preço atual. {escape(ctx.reason)}")
    lines.extend(_recovered_hike_note(ctx))
    normal = ctx.baseline_price or ctx.median_30d
    if normal:
        lines.append(f"Preço normal: {fmt_brl(normal)}")
    lines.append(_footer(ctx))
    return AlertMessage(
        text="\n".join(lines),
        parse_mode="HTML",
        button_text="Ver oferta",
        button_url=item_url(ctx.item_id),
        alert_type="neutro",
    )
