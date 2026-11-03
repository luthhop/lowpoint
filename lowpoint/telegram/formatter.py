from dataclasses import dataclass
from decimal import Decimal
from html import escape


def fmt_brl(value: Decimal) -> str:
    s = f"{value:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def item_url(item_id: str) -> str:
    prefix = item_id[:3]
    number = item_id[3:]
    return f"https://produto.mercadolivre.com.br/{prefix}-{number}"


def _pct(a: Decimal, b: Decimal) -> str:
    if b == 0:
        return "0%"
    return f"{abs((a - b) / b) * 100:.0f}%"


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
        parts.append("\n<b>⚠ Sem garantia informada</b>")
    details: list[str] = []
    if ctx.is_official:
        details.append("Loja oficial")
    else:
        details.append("Vendedor não-oficial")
    if ctx.has_warranty:
        details.append("Com garantia")
    if details and ctx.has_warranty:
        parts.append("\n" + " · ".join(details))
    elif details:
        parts.append("\n" + " · ".join(details))
    if ctx.suspect_count > 0:
        s = "s" if ctx.suspect_count > 1 else ""
        parts.append(f"\n⚠ {ctx.suspect_count} oferta{s} suspeita{s} descartada{s}")
    return "".join(parts)


def _claimed_discount(ctx: AlertContext) -> str | None:
    if ctx.original_price and ctx.original_price > ctx.price:
        pct = _pct(ctx.price, ctx.original_price)
        return f"O anúncio diz {pct} OFF (de {fmt_brl(ctx.original_price)})."
    return None


def format_alert(ctx: AlertContext) -> AlertMessage:
    target_hit = ctx.price <= ctx.target_price

    if target_hit and ctx.verdict == "maquiado":
        return _format_target_hit_maquiado(ctx)
    if target_hit and ctx.verdict == "real":
        return _format_target_hit_real(ctx)
    if ctx.verdict == "real":
        return _format_verdict_real(ctx)
    if ctx.verdict == "maquiado":
        return _format_maquiado(ctx)
    return _format_neutro(ctx)


def _format_target_hit_real(ctx: AlertContext) -> AlertMessage:
    name = escape(ctx.product_name)
    lines = [f"<b>✅ PODE IR</b> · {name} · <b>{fmt_brl(ctx.price)}</b>"]
    lines.append("")
    lines.append(f"Bateu teu alvo de {fmt_brl(ctx.target_price)}.")
    if ctx.median_30d and ctx.median_30d > 0:
        discount = _pct(ctx.price, ctx.median_30d)
        lines.append(
            f"Menor preço em {ctx.monitoring_days} dias. "
            f"Desconto real de {discount} vs. mediana."
        )
    lines.append("")
    if ctx.median_30d:
        lines.append(f"Mediana 30d: {fmt_brl(ctx.median_30d)}")
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


def _format_verdict_real(ctx: AlertContext) -> AlertMessage:
    name = escape(ctx.product_name)
    lines = [f"<b>✅ PODE IR</b> · {name} · <b>{fmt_brl(ctx.price)}</b>"]
    lines.append("")
    if ctx.median_30d and ctx.median_30d > 0:
        discount = _pct(ctx.price, ctx.median_30d)
        lines.append(f"Novo menor preço. Desconto real de {discount} vs. mediana.")
    else:
        lines.append("Novo menor preço.")
    lines.append("")
    if ctx.median_30d:
        lines.append(f"Mediana 30d: {fmt_brl(ctx.median_30d)}")
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
    if ctx.median_30d:
        lines.append(f"Mediana real dos últimos 30 dias: {fmt_brl(ctx.median_30d)}.")
    if ctx.pre_hike_price:
        hike_pct = _pct(ctx.pre_hike_price, ctx.pre_hike_price)
        if ctx.median_30d and ctx.pre_hike_price < ctx.price:
            increase = ((ctx.price - ctx.pre_hike_price) / ctx.pre_hike_price) * 100
            lines.append(
                f"Preço subiu {increase:.0f}% nos 14d antes da "
                f'"queda" (era {fmt_brl(ctx.pre_hike_price)}).'
            )
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
        f"mas o desconto é maquiado."
    )
    claimed = _claimed_discount(ctx)
    if claimed:
        lines.append(claimed)
    if ctx.median_30d:
        lines.append(f"Mediana real dos últimos 30 dias: {fmt_brl(ctx.median_30d)}.")
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
    if ctx.median_30d:
        lines.append(f"Mediana 30d: {fmt_brl(ctx.median_30d)}")
    lines.append(_footer(ctx))
    return AlertMessage(
        text="\n".join(lines),
        parse_mode="HTML",
        button_text="Ver oferta",
        button_url=item_url(ctx.item_id),
        alert_type="neutro",
    )
