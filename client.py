import requests
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any
from models import DEFAULT_TZ

API_BASE_URL = "https://lknpd.nalog.ru/api/v1"


class NpdClient:
    """Класс для взаимодействия с API Мой Налог (НПД)."""
    def __init__(self, token: str):
        self.token = token if token.startswith("Bearer") else f"Bearer {token.strip()}"
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json, text/plain, */*",
            "Authorization": self.token,
            "Origin": "https://lknpd.nalog.ru",
            "Referer": "https://lknpd.nalog.ru/sales/create",
            "User-Agent": "Mozilla/5.0",
        })

    def check_token(self) -> Dict[str, Any]:
        """Проверяет валидность токена и возвращает данные налогоплательщика."""
        resp = self.session.get(f"{API_BASE_URL}/taxpayer", timeout=15)
        resp.raise_for_status()
        return resp.json()

    def register_income(self, payload: Dict[str, Any]) -> requests.Response:
        """Регистрирует новый доход."""
        return self.session.post(f"{API_BASE_URL}/income", json=payload, timeout=40)

    @staticmethod
    def build_payload(
        operation_time_iso: str,
        service_name: str,
        amount: Decimal,
        payment_type: str,
        income_type: str = "FROM_INDIVIDUAL",
    ) -> Dict[str, Any]:
        """Формирует JSON для отправки в API."""
        if amount == amount.to_integral_value():
            amount_value = int(amount)
            total_value = str(int(amount))
        else:
            amount_value = float(amount)
            total_value = str(amount)

        request_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S") + DEFAULT_TZ

        return {
            "operationTime": operation_time_iso,
            "requestTime": request_time,
            "services": [{"name": service_name, "amount": amount_value, "quantity": 1}],
            "totalAmount": total_value,
            "client": {
                "contactPhone": None,
                "displayName": None,
                "inn": None,
                "incomeType": income_type,
            },
            "paymentType": payment_type,
            "ignoreMaxTotalIncomeRestriction": False,
        }
