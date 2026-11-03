# LOWPOINT.

**Os outros te mostram a promoção. O Lowpoint te diz se ela é de verdade.**

> Em construção — o núcleo já funciona, o bot Telegram vem na próxima semana.

---

## O problema

Grupos e apps de promoção mandam centenas de ofertas misturadas. O produto que você quer fica perdido ou você vê tarde demais. Pior: não dá pra saber se o desconto é real ou se o preço foi inflado antes.

## Como o Lowpoint resolve

Bot pessoal no Telegram que monitora produtos específicos no Mercado Livre. Alerta quando o preço atinge o alvo e dá um **veredito claro** com base no histórico de preços:

| Veredito | Significado |
|---|---|
| **Pode ir** | Desconto real — preço abaixo do mínimo histórico |
| **Segura** | Desconto maquiado — preço foi inflado antes de "cair" |
| **Suspeito** | Oferta com preço muito abaixo da mediana (possível golpe) |

O Lowpoint não cria urgência. Ele tira a ansiedade da compra.

## O que já funciona

- Coletor de preços via API oficial do Mercado Livre (endpoint de catálogo)
- Coleta automática a cada hora (GitHub Actions)
- Todas as ofertas de cada coleta armazenadas (offer_snapshots)
- Melhor oferta com proteção anti-golpe (preço < 60% da mediana = suspeita)
- Veredito: detecção de desconto real vs. maquiado
- Desempate inteligente: garantia > loja oficial > preço
- 53 testes

## Roadmap

- [x] Modelo de dados + coletor + veredito
- [ ] Bot Telegram (`/adicionar`, `/lista`, `/remover`, alerta de preço-alvo)
- [ ] Veredito em tempo real nos alertas, bot rodando 24/7
- [ ] Landing page + dashboard (design no Paper)

## Arquitetura

```mermaid
graph LR
    ML["Mercado Livre<br/>/products/{id}/items"] -->|API oficial| C["Coletor<br/>GitHub Actions<br/>1x por hora"]
    C -->|offer_snapshots<br/>price_history| DB[(Neon<br/>PostgreSQL)]
    DB --> V["Veredito<br/>real · maquiado · suspeito"]
    V --> B["Bot Telegram"]
    B -->|alerta com veredito| U["Usuário"]
```

## Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.14 |
| Bot | python-telegram-bot |
| Banco | PostgreSQL (Neon cloud) |
| ORM | SQLAlchemy 2 + Alembic |
| Fonte de preços | API oficial do ML (catálogo) |
| Coleta 24/7 | GitHub Actions (cron) |
| Testes | pytest |
| Design | Paper |
| Tipos monetários | `NUMERIC(12,2)` no banco, `Decimal` no Python — nunca `float` |

## Rodando localmente

### Pré-requisitos

- Python 3.14+
- Conta de desenvolvedor no Mercado Livre (para client_id/secret)
- Neon (cloud) **ou** Docker para o PostgreSQL

### Setup

```bash
# Clonar
git clone https://github.com/lucaslimadossantos1206/lowpoint.git
cd lowpoint

# Dependências
pip install -r requirements.txt

# Variáveis de ambiente
cp .env.example .env
# Editar .env com suas credenciais
```

### Banco de dados

**Opção A — Neon (produção):**
```bash
# DATABASE_URL no .env apontando para o Neon
alembic upgrade head
```

**Opção B — Docker (dev local):**
```bash
docker compose up -d
# DATABASE_URL=postgresql+psycopg2://lowpoint:lowpoint_dev@localhost:5432/lowpoint
alembic upgrade head
```

### Migrar tokens do ML

```bash
# Colocar tokens em ml_tokens.json (ver .env.example para o formato)
python scripts/migrate_ml_tokens.py
```

### Registrar um produto

```bash
python -m lowpoint.register --url "https://www.mercadolivre.com.br/p/MLB57081243" --target 3500
```

### Rodar uma coleta

```bash
python -m lowpoint.collect --once
```

### Testes

```bash
python -m pytest -v
```

## Decisões técnicas

O registro completo está em [`memoria/decisoes.md`](memoria/decisoes.md). Destaques:

- **Por que não scraping?** Viola a cláusula 7.6 dos Termos de Desenvolvedores do ML e o projeto é público. Usamos o endpoint oficial `/products/{id}/items`.
- **Por que guardar todas as ofertas?** A tabela `offer_snapshots` guarda cada oferta de cada coleta. `price_history` guarda só a melhor oferta (derivada). Isso permite recalcular o histórico quando a regra muda.
- **Como funciona a proteção anti-golpe?** Ofertas com preço abaixo de 60% da mediana da coleta são marcadas como suspeitas e excluídas da melhor oferta. O threshold é configurável.
- **Como funciona o veredito "maquiado"?** `original_price > mediana_30d * 1.10` OU preço subiu >10% nos 14 dias antes da queda.
- **Por que Decimal e nunca float?** Aritmética de ponto flutuante gera erros de arredondamento em valores monetários.

## Como foi construído

Projeto inteiro construído com IA como copiloto:

- **[Claude Code](https://claude.com/claude-code)** — arquitetura, código, testes, decisões técnicas
- **[Obsidian](https://obsidian.md/)** como memória persistente — o vault em [`memoria/`](memoria/) documenta cada decisão e o estado do projeto entre sessões
- **[Paper](https://paper.design/)** para todo o design — branding board, exploração visual, componentes

O processo também é o produto: o vault de memória fica no repositório, mostrando como o Lowpoint foi construído.

---

MIT License
