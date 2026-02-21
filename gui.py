import os
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime

import requests
import customtkinter as ctk

from client import NpdClient
from utils import YookassaCsvReader, StateManager, load_config, save_config, CONFIG_PATH

DEFAULT_SERVICE_NAME = "Пополнение баланса в сервисе"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._load_initial_config()

    def _setup_ui(self):
        """Инициализация элементов интерфейса."""
        self.title("YooKassa to NPD")
        self.geometry("800x700")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # Настройка сетки главного окна
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)  # Текстовое поле логов будет растягиваться

        # --- 1. Секция Токена ---
        self.token_label = ctk.CTkLabel(
            self, text="Токен (Bearer ...):", font=ctk.CTkFont(weight="bold")
        )
        self.token_label.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")

        self.token_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.token_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.token_frame.grid_columnconfigure(0, weight=1)

        self.token_entry = ctk.CTkEntry(
            self.token_frame, placeholder_text="Введите ваш токен здесь"
        )
        self.token_entry.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.check_token_button = ctk.CTkButton(
            self.token_frame, text="Проверить", command=self.check_token, width=120
        )
        self.check_token_button.grid(row=0, column=1)

        # --- 2. Секция Файла ---
        self.file_label = ctk.CTkLabel(
            self, text="Файл выгрузки ЮKassa (CSV):", font=ctk.CTkFont(weight="bold")
        )
        self.file_label.grid(row=2, column=0, padx=20, pady=(10, 5), sticky="w")

        self.file_frame = ctk.CTkFrame(self)
        self.file_frame.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.file_frame.grid_columnconfigure(0, weight=1)

        self.file_path_entry = ctk.CTkEntry(self.file_frame, placeholder_text="Путь к CSV файлу")
        self.file_path_entry.grid(row=0, column=0, padx=(10, 10), pady=10, sticky="ew")

        self.browse_button = ctk.CTkButton(
            self.file_frame, text="Обзор", command=self.browse_file, width=120
        )
        self.browse_button.grid(row=0, column=1, padx=(0, 10), pady=10)

        # --- 3. Секция Настроек и Управления ---
        self.settings_frame = ctk.CTkFrame(self)
        self.settings_frame.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        self.settings_frame.grid_columnconfigure(2, weight=1)

        # Режим названия услуги
        ctk.CTkLabel(self.settings_frame, text="Название услуги:").grid(
            row=0, column=0, padx=10, pady=(10, 5), sticky="w"
        )
        self.service_name_mode = tk.StringVar(value="custom")
        self.service_mode_menu = ctk.CTkOptionMenu(
            self.settings_frame,
            values=["Свое название", "Из описания в CSV"],
            command=self._on_service_mode_change,
            width=150
        )
        self.service_mode_menu.set("Свое название")
        self.service_mode_menu.grid(row=0, column=1, padx=10, pady=(10, 5), sticky="w")

        self.service_name_entry = ctk.CTkEntry(
            self.settings_frame, placeholder_text="Введите название услуги"
        )
        self.service_name_entry.insert(0, DEFAULT_SERVICE_NAME)
        self.service_name_entry.grid(row=0, column=2, padx=10, pady=(10, 5), sticky="ew")

        # Кнопка СТАРТ
        self.start_button = ctk.CTkButton(
            self.settings_frame,
            text="ЗАПУСТИТЬ ОТПРАВКУ",
            command=self.start_processing,
            fg_color="green",
            hover_color="darkgreen",
            height=45,
            font=ctk.CTkFont(weight="bold")
        )
        self.start_button.grid(row=1, column=0, columnspan=3, padx=10, pady=(5, 10), sticky="ew")

        # --- 4. Секция Логов ---
        self.log_label = ctk.CTkLabel(self, text="Лог выполнения:", font=ctk.CTkFont(weight="bold"))
        self.log_label.grid(row=5, column=0, padx=20, pady=(10, 0), sticky="w")

        self.log_textbox = ctk.CTkTextbox(self, height=200)
        self.log_textbox.grid(row=6, column=0, padx=20, pady=(5, 10), sticky="nsew")

        # --- 5. Секция Прогресса ---
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.grid(row=7, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.grid(row=0, column=0, sticky="ew")
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            self.progress_frame, text="Готов к работе", font=ctk.CTkFont(size=11)
        )
        self.progress_label.grid(row=1, column=0, pady=(2, 0))

        # Настройка растяжения окна
        self.grid_rowconfigure(6, weight=1)

    def _on_service_mode_change(self, choice):
        if choice == "Из описания в CSV":
            self.service_name_entry.configure(state="disabled")
            self.service_name_mode.set("csv")
        else:
            self.service_name_entry.configure(state="normal")
            self.service_name_mode.set("custom")

    def log(self, message: str):
        self.log_textbox.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_textbox.see(tk.END)

    def browse_file(self):
        filename = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if filename:
            self.file_path_entry.delete(0, tk.END)
            self.file_path_entry.insert(0, filename)

    def _load_initial_config(self):
        config = load_config()
        if config:
            self.token_entry.insert(0, config.get("token", ""))
            self.file_path_entry.insert(0, config.get("last_file", ""))

            saved_service_name = config.get("service_name", DEFAULT_SERVICE_NAME)
            self.service_name_entry.delete(0, tk.END)
            self.service_name_entry.insert(0, saved_service_name)

            saved_mode = config.get("service_mode", "Свое название")
            self.service_mode_menu.set(saved_mode)
            self._on_service_mode_change(saved_mode)

    def _save_current_config(self):
        config = {
            "token": self.token_entry.get(),
            "last_file": self.file_path_entry.get(),
            "service_name": self.service_name_entry.get(),
            "service_mode": self.service_mode_menu.get()
        }
        save_config(config)

    def check_token(self):
        token = self.token_entry.get().strip()
        if not token:
            messagebox.showwarning("Внимание", "Сначала введите токен!")
            return

        self.check_token_button.configure(state="disabled", text="Проверка...")

        def _thread_target():
            try:
                client = NpdClient(token)
                data = client.check_token()
                name, inn = data.get("displayName", "Пользователь"), data.get("inn", "неизвестен")
                self.after(
                    0, lambda: messagebox.showinfo(
                        "Успех", f"Токен валиден!\n\nФИО: {name}\nИНН: {inn}"
                    )
                )
                self.after(0, lambda: self.log(f"Токен проверен: {name} (ИНН {inn})"))
            except Exception as e:
                err_text = str(e)
                self.after(
                    0, lambda m=err_text: messagebox.showerror("Ошибка", f"Токен невалиден:\n{m}")
                )
            finally:
                self.after(
                    0, lambda: self.check_token_button.configure(state="normal", text="Проверить")
                )

        threading.Thread(target=_thread_target, daemon=True).start()

    def start_processing(self):
        token, file_path = self.token_entry.get().strip(), self.file_path_entry.get().strip()
        service_name_custom = self.service_name_entry.get().strip()
        service_mode = self.service_name_mode.get()

        if not token or not file_path:
            messagebox.showerror("Ошибка", "Заполните токен и выберите файл!")
            return

        if service_mode == "custom" and not service_name_custom:
            messagebox.showerror("Ошибка", "Введите название услуги!")
            return

        if not os.path.exists(file_path):
            messagebox.showerror("Ошибка", f"Файл не найден: {file_path}")
            return

        self._save_current_config()
        self.start_button.configure(state="disabled")
        self.log_textbox.delete("1.0", tk.END)
        threading.Thread(
            target=self._process_csv_thread,
            args=(token, file_path, "CASH", service_mode, service_name_custom), daemon=True
        ).start()

    def _process_csv_thread(
        self,
        token: str,
        file_path: str,
        payment_type: str,
        service_mode: str,
        service_name_custom: str
    ):
        try:
            client = NpdClient(token)
            done_ids = StateManager.load_done_ids()
            rows = YookassaCsvReader.read(file_path)
            total, processed = len(rows), 0

            self.log(f"Найдено платежей: {total}")

            for idx, r in enumerate(rows, start=1):
                self.progress_bar.set(idx / total)
                self.progress_label.configure(text=f"Обработано {idx} из {total}")

                if r.payment_id in done_ids:
                    self.log(f"Пропуск (уже был): {r.payment_id}")
                    continue
                if not r.is_paid:
                    self.log(f"Пропуск (статус {r.status}): {r.payment_id}")
                    continue

                try:
                    if service_mode == "csv":
                        service_name = r.description or DEFAULT_SERVICE_NAME
                    else:
                        service_name = service_name_custom

                    amount = r.parse_amount()
                    payload = client.build_payload(
                        r.get_operation_time_iso(), service_name, amount, payment_type
                    )

                    success = self._send_with_retry(client, r.payment_id, payload, idx)
                    if success:
                        StateManager.save_done_id(r.payment_id)
                        done_ids.add(r.payment_id)
                        processed += 1
                        self.log(f"OK: {r.payment_id} ({amount} руб.) -> {service_name}")

                except Exception as e:
                    self.log(f"Ошибка строки {r.payment_id}: {e}")

            self.log(f"Завершено! Создано чеков: {processed}")
            self.progress_label.configure(text=f"Завершено! Создано: {processed}")
            self.after(
                0, lambda: messagebox.showinfo(
                    "Готово", f"Обработка завершена.\nСоздано чеков: {processed}"
                )
            )
        except Exception as e:
            err_text = str(e)
            self.after(0, lambda m=err_text: messagebox.showerror("Критическая ошибка", m))
        finally:
            self.after(0, lambda: self.start_button.configure(state="normal"))

    def _send_with_retry(self, client: NpdClient, payment_id: str, payload: dict, idx: int) -> bool:
        for attempt in range(1, 4):
            try:
                resp = client.register_income(payload)
                ok = resp.status_code in (200, 201)

                StateManager.log_event(
                    {
                        "idx": idx, "payment_id": payment_id, "ok": ok,
                        "status": resp.status_code, "attempt": attempt, "response": resp.text[:1000]
                    }
                )

                if ok:
                    return True
                if resp.status_code in (401, 403):
                    raise Exception("Ошибка авторизации (401/403).")
                if resp.status_code in (429, 500, 502, 503, 504):
                    time.sleep(2 * attempt)
                    continue
                return False
            except requests.RequestException:
                time.sleep(2 * attempt)
        return False


if __name__ == "__main__":
    App().mainloop()
