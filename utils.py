import csv
import json
import os
from typing import List, Set, Dict, Any
from models import PaymentRow

LOG_PATH = "npd_import_log.jsonl"
STATE_PATH = "npd_import_done_ids.txt"
CONFIG_PATH = "config.json"


class StateManager:
    """Класс для управления состоянием (обработанные ID и логи)."""
    @staticmethod
    def load_done_ids() -> Set[str]:
        if not os.path.exists(STATE_PATH):
            return set()
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}

    @staticmethod
    def save_done_id(payment_id: str) -> None:
        with open(STATE_PATH, "a", encoding="utf-8") as f:
            f.write(payment_id + "\n")

    @staticmethod
    def log_event(event: Dict[str, Any]) -> None:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")


class YookassaCsvReader:
    """Класс для чтения CSV выгрузок ЮKassa."""
    @staticmethod
    def read(path: str) -> List[PaymentRow]:
        rows: List[PaymentRow] = []
        # Пробуем разные кодировки
        encodings = ["utf-8-sig", "windows-1251", "utf-8"]
        content = None
        used_encoding = None
        
        for enc in encodings:
            try:
                with open(path, "r", encoding=enc) as f:
                    content = f.read()
                if content and (";" in content or "," in content):
                    used_encoding = enc
                    break
            except Exception:
                continue
        
        if not content:
            raise ValueError("Не удалось прочитать файл или файл пуст.")

        # Определяем разделитель
        delimiter = ";" if ";" in content else ","
        
        # Читаем строки вручную для отладки и надежности
        import io
        f = io.StringIO(content)
        reader = csv.DictReader(f, delimiter=delimiter)
        
        # Очищаем заголовки
        if reader.fieldnames:
            reader.fieldnames = [fn.strip().replace('\ufeff', '') for fn in reader.fieldnames]
        
        for i, row in enumerate(reader, start=2):
            # Очищаем ключи и значения
            clean_row = {str(k).strip(): str(v).strip() for k, v in row.items() if k is not None}
            
            if not clean_row or not any(clean_row.values()):
                continue

            # Ищем нужные колонки, игнорируя регистр
            def get_val(possible_names: List[str]) -> str:
                for name in possible_names:
                    for key in clean_row.keys():
                        if key.lower() == name.lower():
                            return clean_row[key]
                return ""

            p_id = get_val(["Идентификатор платежа", "payment_id", "id"])
            p_status = get_val(["Статус платежа", "payment_status", "status"])
            p_date = get_val(["Дата платежа", "payment_date", "paid_at"])
            p_amount = get_val(["Сумма платежа", "payment_amount", "amount"])
            
            # Если основные поля найдены, добавляем строку
            if p_id and p_date and p_amount:
                rows.append(
                    PaymentRow(
                        payment_id=p_id,
                        paid_at_raw=p_date,
                        status=p_status,
                        amount_raw=p_amount,
                        description=get_val(["Описание заказа", "order_description", "description"]),
                        method=get_val(["Метод платежа", "payment_method", "method"]),
                    )
                )
        
        return rows


def load_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(config: Dict[str, Any]) -> None:
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f)
