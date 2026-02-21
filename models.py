from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

DEFAULT_TZ = "+03:00"


@dataclass(frozen=True)
class PaymentRow:
    """Структура данных для одной строки из CSV ЮKassa."""
    payment_id: str
    paid_at_raw: str
    status: str
    amount_raw: str
    description: str
    method: str

    @property
    def is_paid(self) -> bool:
        """Проверяет, оплачен ли платеж."""
        return self.status == "Оплачен"

    def parse_amount(self) -> Decimal:
        """Преобразует строку суммы в Decimal."""
        s = (self.amount_raw or "").strip().replace(" ", "").replace(",", ".")
        return Decimal(s)

    def get_operation_time_iso(self, tz: str = DEFAULT_TZ) -> str:
        """Преобразует дату платежа в ISO формат для API."""
        dt = datetime.strptime(self.paid_at_raw.strip(), "%d.%m.%Y %H:%M:%S")
        return dt.strftime("%Y-%m-%dT%H:%M:%S") + tz
