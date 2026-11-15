"""Única fonte das regras da análise: transcrição do pré-registro v1 + Emendas 1 e 2.

Documento: memoria/analise/plano-pre-registro.md (tag git pre-registro-v1, Emendas 1 e 2).
Cada constante cita a seção de onde saiu. Nada aqui deve ser ajustado depois
de ver os dados; mudança só por emenda datada no documento.
"""
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

DOC = "memoria/analise/plano-pre-registro.md"
TAG = "pre-registro-v1"
# Cabeçalho: "Código das regras: commit 65ed7ef".
RULES_COMMIT = "65ed7ef"
# Arquivos cujo comportamento o replay de P1a usa ("O que NÃO muda": commit das regras).
FROZEN_FILES = ("lowpoint/verdict.py",)

# "Definições comuns › Horário": America/Sao_Paulo (sem horário de verão desde 2019).
BRT = timezone(timedelta(hours=-3))


@dataclass(frozen=True)
class Window:
    """Janela semiaberta [start, end). rate = coletas esperadas por hora."""
    name: str
    start: datetime
    end: datetime
    rate: int

    def contains(self, t: datetime) -> bool:
        return self.start <= t < self.end

    def status(self, now: datetime) -> str:
        if now >= self.end:
            return "completa"
        if now >= self.start:
            return "em andamento"
        return "futura"


def _brt(d, m, h=0, mi=0):
    return datetime(2026, m, d, h, mi, tzinfo=BRT)


# "Definições comuns › Janelas" (fixas, sem sobreposição) e
# "Cobertura mínima" (≈ 1/h fora da BF, ≈ 4/h na BF).
WINDOWS = (
    Window("B0", _brt(14, 11, 14, 50), _brt(17, 11, 14, 50), 1),
    Window("PRE", _brt(17, 11, 14, 50), _brt(23, 11), 1),
    Window("BF", _brt(23, 11), _brt(28, 11), 4),
    Window("POS", _brt(28, 11), _brt(8, 12), 1),
)
W = {w.name: w for w in WINDOWS}
# "Coleta": dataset cortado em 08/12 00:00.
CUTOFF = _brt(8, 12)
# "P4": B0 + Pré-BF juntas como "antes".
ANTES = Window("antes", W["B0"].start, W["PRE"].end, 1)
# "P5 › amplitude no período todo".
PERIODO = Window("periodo", W["B0"].start, CUTOFF, 1)

# "Definições comuns › Cobertura mínima".
MIN_COVERAGE = Decimal("0.70")

# "Definições comuns › Limiares": os do lowpoint/config.py no commit 65ed7ef.
# Os três últimos não aparecem no texto, mas fazem parte do compute_verdict
# congelado usado em P1a, então também são vigiados.
EXPECTED_THRESHOLDS = {
    "REAL_DISCOUNT_THRESHOLD": Decimal("0.05"),
    "HIKE_THRESHOLD": Decimal("0.10"),
    "FACHADA_THRESHOLD": Decimal("0.03"),
    "HIKE_RETREAT_THRESHOLD": Decimal("0.05"),
    "INFLATED_ORIGINAL_THRESHOLD": Decimal("1.10"),
    "MIN_MONITORING_DAYS": 7,
    "MEDIAN_WINDOW_DAYS": 30,
    "PRICE_HIKE_WINDOW_DAYS": 14,
}
REAL = EXPECTED_THRESHOLDS["REAL_DISCOUNT_THRESHOLD"]          # P1b
HIKE = EXPECTED_THRESHOLDS["HIKE_THRESHOLD"]                   # P2 subida
FACHADA = EXPECTED_THRESHOLDS["FACHADA_THRESHOLD"]             # P2 fachada
RETREAT = EXPECTED_THRESHOLDS["HIKE_RETREAT_THRESHOLD"]        # P2 queda
INFLATED = EXPECTED_THRESHOLDS["INFLATED_ORIGINAL_THRESHOLD"]  # P3

# "P1a/P1b › Conta": ≥ 2 coletas consecutivas; sensibilidade ≥ 1.
STREAK = 2
# "P4 › Classificação": vence se ≥ 1% menor que o segundo menor.
P4_TIE = Decimal("0.01")
# "P5 › Esperado dos controles" e "os 18 ≥ 5%".
P5_FLAT = Decimal("0.05")

# "Emenda 2 › Cobertura": produto < 70% numa janela usada é excluído daquela
# pergunta; cortes de manchete viram proporção dos produtos com cobertura
# (frações exatas, para 10 de 18 continuar sendo "a maioria"); manchete só com
# ≥ 12 dos 18 não-controle cobertos.
P1_MAJORITY = Fraction(10, 18)   # ≈ 55,6%
P1_NONE = Fraction(4, 18)        # ≈ 22,2%
P2_COMMON = Fraction(5, 18)      # ≈ 27,8%
MIN_COVERED = 12

# "Dados exploratórios" + "Emenda 1": primeira coleta com deal_ids/tags.
EMENDA1_START = datetime(2026, 11, 15, 9, 45, 29, tzinfo=BRT)
# "Limitações › Produtos com histórico mais longo": sensibilidade exploratória.
LONG_REF_WATCHES = (2, 4, 5)


@dataclass(frozen=True)
class Product:
    watch_id: int
    catalog_id: str
    label: str
    group: str  # "pessoal" | "analise" | "controle"


# "Amostra": 20 produtos (watch 1 fora). Pessoais: watches 2, 4, 5.
# Análise e controles: memoria/analise-bf.md (watches 6–22, na ordem).
PRODUCTS = (
    Product(2, "MLB57081243", "PS5 Slim Digital", "pessoal"),
    Product(4, "MLB79391475", 'LG UltraGear 27"', "pessoal"),
    Product(5, "MLB59323822", 'AOC AGON 27"', "pessoal"),
    Product(6, "MLB75001430", "TV LG 50 QNED70", "analise"),
    Product(7, "MLB48808732", "TV TCL 55 C6K", "analise"),
    Product(8, "MLB67919726", "Soundbar Fortrek", "analise"),
    Product(9, "MLB69393461", "Fone JBL Tune 530BT", "analise"),
    Product(10, "MLB68445612", "JBL Go 5", "analise"),
    Product(11, "MLB47111905", "Galaxy A36 256GB", "analise"),
    Product(12, "MLB64222225", "Moto G06", "analise"),
    Product(13, "MLB1055309009", "iPhone 17 256GB", "analise"),
    Product(14, "MLB70040749", "Notebook Dell i5", "analise"),
    Product(15, "MLB19672271", "Air fryer Xiaomi 3,5L", "analise"),
    Product(16, "MLB62963466", "Robô Xiaomi S20+", "analise"),
    Product(17, "MLB17484025", "Micro-ondas Philco 20L", "analise"),
    Product(18, "MLB15261607", "Nespresso Essenza Mini", "analise"),
    Product(19, "MLB28083897", "DualSense Cobalt", "analise"),
    Product(20, "MLB49200061", "Nintendo Switch 2", "analise"),
    Product(21, "MLB26967981", "Pilha Duracell AA (2)", "controle"),
    Product(22, "MLB19400333", "Livro O Alquimista", "controle"),
)
NON_CONTROL = tuple(p for p in PRODUCTS if p.group != "controle")
CONTROLS = tuple(p for p in PRODUCTS if p.group == "controle")

_ROOT = Path(__file__).resolve().parent.parent


def check_guard(config, *, check_git: bool = True) -> list[str]:
    """Lista de problemas; vazia = regras iguais às do pré-registro."""
    problems = []
    for name, expected in EXPECTED_THRESHOLDS.items():
        if not hasattr(config, name):
            problems.append(f"{name} ausente do config.py (pré-registro: {expected})")
            continue
        actual = getattr(config, name)
        if actual != expected:
            problems.append(f"{name} = {actual} no config.py, pré-registro = {expected}")
    if check_git:
        try:
            r = subprocess.run(
                ["git", "diff", "--quiet", RULES_COMMIT, "--", *FROZEN_FILES],
                cwd=_ROOT, capture_output=True,
            )
        except OSError as e:
            problems.append(f"não deu para verificar {FROZEN_FILES} contra {RULES_COMMIT}: {e}")
        else:
            if r.returncode == 1:
                problems.append(f"{', '.join(FROZEN_FILES)} difere do commit {RULES_COMMIT}")
            elif r.returncode != 0:
                problems.append(f"git diff falhou ao comparar com {RULES_COMMIT}")
    return problems
