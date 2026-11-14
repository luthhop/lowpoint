from datetime import timedelta
from decimal import Decimal

MIN_MONITORING_DAYS = 7
MEDIAN_WINDOW_DAYS = 30
PRICE_HIKE_WINDOW_DAYS = 14
REAL_DISCOUNT_THRESHOLD = Decimal("0.05")
HIKE_THRESHOLD = Decimal("0.10")
INFLATED_ORIGINAL_THRESHOLD = Decimal("1.10")
FACHADA_THRESHOLD = Decimal("0.03")

# Watches por chat. Silenciosos (produtos de análise) têm teto próprio e não
# ocupam vaga do limite normal do /adicionar.
MAX_WATCHES_PER_CHAT = 20
MAX_SILENT_WATCHES_PER_CHAT = 40

# Anti-spam por watch (lowpoint/antispam.py)
ALERT_MIN_INTERVAL = timedelta(hours=1)          # teto geral: 1 alerta/h, qualquer tipo
REPEAT_ALERT_MIN_DROP = Decimal("0.03")          # real/target_hit repetido: ≥3% abaixo do último
MAQUIADO_REPEAT_INTERVAL = timedelta(hours=24)   # maquiado repetido: no máximo 1 a cada 24h
