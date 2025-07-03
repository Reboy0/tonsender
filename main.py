#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
import sys
from typing import List, Optional
from decimal import Decimal
import json
import time
import requests

# Colorama
try:
    from colorama import Fore, Back, Style, init
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    print("Увага: colorama не встановлено. Запустіть: pip install colorama")
    COLORAMA_AVAILABLE = False
    class MockColor:
        def __getattr__(self, name): return ""
    Fore = Back = Style = MockColor()
    def init(**kwargs): pass

# TON SDK
TON_SDK_AVAILABLE = False
try:
    from tonsdk.provider import ToncenterClient
    from tonsdk.utils import to_nano, from_nano, Address
    from tonsdk.contract.wallet import Wallets, WalletVersionEnum
    from tonsdk.boc import Cell
    TON_SDK_AVAILABLE = True
except ImportError as e:
    print(f"Помилка імпорту tonsdk: {e}")
    print("Встановіть: pip install tonsdk")
    response = input("\nПродовжити без TON SDK для демонстрації? (y/n): ")
    if response.lower() != 'y':
        sys.exit(1)

class TONBatchTransfer:
    def __init__(self):
        self.client = None
        self.wallet = None
        self.seed_phrase = None
        self.addresses = []
        self.demo_mode = not TON_SDK_AVAILABLE

    def print_colored(self, message: str, color: str = "", style: str = ""):
        if COLORAMA_AVAILABLE:
            print(f"{style}{color}{message}{Style.RESET_ALL}")
        else:
            print(message)

    def print_header(self, text: str):
        if COLORAMA_AVAILABLE:
            print(f"\n{Back.BLUE}{Fore.WHITE} {text} {Style.RESET_ALL}")
        else:
            print(f"\n{'=' * 50}\n {text}\n{'=' * 50}")

    def print_success(self, text: str):
        self.print_colored(f"✅ {text}", Fore.GREEN, Style.BRIGHT)

    def print_error(self, text: str):
        self.print_colored(f"❌ {text}", Fore.RED, Style.BRIGHT)

    def print_warning(self, text: str):
        self.print_colored(f"⚠️  {text}", Fore.YELLOW, Style.BRIGHT)

    def print_info(self, text: str):
        self.print_colored(f"ℹ️  {text}", Fore.CYAN)

    def check_dependencies(self):
        self.print_header("ПЕРЕВІРКА ЗАЛЕЖНОСТЕЙ")
        if not TON_SDK_AVAILABLE:
            self.print_error("TON SDK не встановлено!")
            self.print_warning("Запуск у демо-режимі...")
            self.demo_mode = True
            return False
        self.print_success("Усі залежності встановлено")
        return True

    def setup_wallet(self):
        self.print_header("НАЛАШТУВАННЯ ГАМАНЦЯ")
        if self.demo_mode:
            self.print_warning("Демо-режим: імітація налаштування гаманця")
            self.seed_phrase = ["demo"] * 24
            return True

        print("1. Ввести seed вручну\n2. Зчитати з файлу")
        choice = input("Ваш вибір (1 або 2): ").strip()
        
        if choice == "1":
            seed_input = input("Введіть seed фразу (24 слова): ").strip()
            self.seed_phrase = seed_input.split()
        elif choice == "2":
            filename = input("Файл з seed фразою: ").strip()
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    self.seed_phrase = f.read().strip().split()
                self.print_success("Seed зчитано")
            except Exception as e:
                self.print_error(f"Помилка читання файлу: {e}")
                return False
        else:
            self.print_error("Невірний вибір!")
            return False

        if len(self.seed_phrase) != 24:
            self.print_error("Seed повинен мати 24 слова!")
            return False

        # Діагностика: показати всі можливі адреси для різних версій і wallet_id
        try:
            from tonsdk.contract.wallet import WalletVersionEnum
            versions = [
                ("v4r1", WalletVersionEnum.v4r1),
                ("v4r1", WalletVersionEnum.v3r1),
                ("v4r1", WalletVersionEnum.v3r2),
                ("v4r2", WalletVersionEnum.v4r2)
            ]
            wallet_ids = [0]
            candidates = []
            print("\nМожливі адреси для вашої seed-фрази:")
            idx = 1
            for vname, v in versions:
                for wid in wallet_ids:
                    try:
                        _mn, pub_k, priv_k, wallet = Wallets.from_mnemonics(
                            self.seed_phrase, v, wid
                        )
                        addr = wallet.address.to_string(True, True, True)
                        print(f"{idx}. Версія: {vname}, wallet_id: {wid}, адреса: {addr}")
                        candidates.append((v, wid, addr))
                        idx += 1
                    except Exception as e:
                        print(f"{idx}. Версія: {vname}, wallet_id: {wid}, помилка: {e}")
                        candidates.append((v, wid, None))
                        idx += 1
            print("\nВведіть номер потрібної адреси (1-{}):".format(len(candidates)))
            while True:
                sel = input("Ваш вибір: ").strip()
                if sel.isdigit() and 1 <= int(sel) <= len(candidates):
                    sel = int(sel) - 1
                    break
                print("Невірний вибір! Спробуйте ще раз.")
            v, wid, addr = candidates[sel]
            if addr is None:
                self.print_error("Обрана комбінація не створила адресу. Спробуйте іншу.")
                return False
            # Ініціалізація клієнта TonCenter
            self.client = ToncenterClient(
                base_url="https://toncenter.com/api/v2/",
                api_key="dfe1ace1a6c6a9628e03dee42d2df1c4aeab9114aca025f409bf8037aff801fa"
            )
            # Створення гаманця з вибраними параметрами
            _mn, pub_k, priv_k, wallet = Wallets.from_mnemonics(
                self.seed_phrase, v, wid
            )
            wallet.provider = self.client
            self.wallet = wallet
            self.print_success("Гаманець готовий!")
            self.print_info(f"Адреса: {addr}")
            self.print_info(f"Версія: {v.name}, wallet_id: {wid}")
            return True
        except Exception as e:
            self.print_error(f"Помилка діагностики/ініціалізації гаманця: {e}")
            return False

    def load_addresses(self):
        self.print_header("ЗАВАНТАЖЕННЯ АДРЕС")
        filename = input("Файл з адресами: ").strip()
        
        if not os.path.exists(filename):
            self.print_error("Файл не знайдено")
            return False
            
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                raw = [line.strip() for line in f.readlines() if line.strip()]
                
            self.addresses = []
            for addr in raw:
                try:
                    # Перевірка валідності адреси
                    Address(addr)
                    self.addresses.append(addr)
                except Exception as e:
                    self.print_warning(f"Пропущено невалідну адресу: {addr}")
                    
            if not self.addresses:
                self.print_error("Немає валідних адрес")
                return False
                
            self.print_success(f"Завантажено {len(self.addresses)} адрес")
            return True
            
        except Exception as e:
            self.print_error(f"Помилка читання: {e}")
            return False

    async def get_wallet_balance(self):
        if self.demo_mode:
            return Decimal('10.0')
            
        try:
            # Отримання адреси у правильному форматі
            addr = self.wallet.address.to_string(True, True, True)
            url = f"https://toncenter.com/api/v2/getAddressBalance?address={addr}"
            
            resp = requests.get(url, timeout=10)
            data = resp.json()
            
            if data.get("ok") and "result" in data:
                balance_nano = int(data["result"])
                # Конвертація з нанотонів в TON
                return Decimal(str(balance_nano / 1_000_000_000))
            else:
                self.print_error(f"Помилка API: {data}")
                return Decimal('0')
                
        except Exception as e:
            self.print_error(f"Не вдалося отримати баланс: {e}")
            return Decimal('0')

    def get_transfer_amount(self, balance):
        self.print_header("СУМА ДЛЯ ПЕРЕКАЗУ")
        print("1. Загальна сума\n2. Сума на кожен адрес")
        choice = input("Ваш вибір: ").strip()
        
        try:
            if choice == '1':
                total = float(input("Загальна сума (TON): "))
                if total <= 0:
                    self.print_error("Сума повинна бути більше нуля")
                    return None, None
                    
                per = total / len(self.addresses)
                
                # Перевірка чи вистачає коштів (з урахуванням комісій)
                estimated_fees = len(self.addresses) * 0.01  # Приблизна комісія на транзакцію
                if total + estimated_fees > float(balance):
                    self.print_error(f"Недостатньо коштів. Потрібно: {total + estimated_fees:.4f} TON")
                    return None, None
                    
                return Decimal(str(per)), "загальна"
                
            elif choice == '2':
                per = float(input("Сума на кожен адрес (TON): "))
                if per <= 0:
                    self.print_error("Сума повинна бути більше нуля")
                    return None, None
                    
                total = per * len(self.addresses)
                estimated_fees = len(self.addresses) * 0.01
                
                if total + estimated_fees > float(balance):
                    self.print_error(f"Недостатньо коштів. Потрібно: {total + estimated_fees:.4f} TON")
                    return None, None
                    
                return Decimal(str(per)), "на кожен"
                
        except ValueError:
            self.print_error("Невірна сума")
        except Exception as e:
            self.print_error(f"Помилка: {e}")
            
        return None, None

    async def send_transaction(self, to_address: str, amount: Decimal):
        if self.demo_mode:
            await asyncio.sleep(0.1)
            return {"hash": f"demo_hash_{to_address[:8]}"}
            
        try:
            # Конвертація суми в нанотони (1 TON = 1,000,000,000 нанотонів)
            amount_nano = int(float(amount) * 1_000_000_000)
            
            # Отримання поточного seqno
            seqno = await self.get_seqno()
            
            # Створення внутрішнього повідомлення
            internal_message = {
                "to": Address(to_address),
                "value": amount_nano,
                "bounce": False,
                "body": None
            }
            
            # Створення зовнішнього повідомлення (без bounce, бо не підтримується)
            external_message = self.wallet.create_transfer_message(
                to_addr=internal_message["to"],
                amount=internal_message["value"],
                seqno=seqno,
                payload=internal_message["body"],
                send_mode=3
            )
            
            # Серіалізація в BOC
            boc_data = external_message["message"].to_boc(False)
            
            # Відправка транзакції
            result = await self.send_boc_to_network(boc_data)
            
            if result.get("ok"):
                return {"hash": result.get("result", {}).get("hash")}
            else:
                self.print_error(f"Помилка API: {result}")
                return None
                
        except Exception as e:
            self.print_error(f"Помилка для {to_address}: {e}")
            return None

    async def send_boc_to_network(self, boc_data):
        """Відправка BOC через HTTP API"""
        try:
            import base64
            
            # Кодування BOC в base64
            boc_base64 = base64.b64encode(boc_data).decode('utf-8')
            
            # Відправка через HTTP API
            url = "https://toncenter.com/api/v2/sendBoc"
            data = {
                "boc": boc_base64
            }
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            resp = requests.post(url, json=data, headers=headers, timeout=15)
            result = resp.json()
            
            # Детальне логування для діагностики
            if not result.get("ok"):
                self.print_error(f"Детальна помилка API: {result}")
                
            return result
            
        except Exception as e:
            self.print_error(f"Помилка відправки BOC: {e}")
            return {"ok": False, "error": str(e)}

    async def get_seqno(self):
        """Отримання sequence number для гаманця"""
        if self.demo_mode:
            return 1
            
        try:
            addr = self.wallet.address.to_string(True, True, True)
            url = f"https://toncenter.com/api/v2/getAddressInformation?address={addr}"
            
            resp = requests.get(url, timeout=10)
            data = resp.json()
            
            if data.get("ok") and "result" in data:
                seqno = data["result"].get("seqno", 0)
                self.print_info(f"Поточний seqno: {seqno}")
                return seqno
            else:
                self.print_error(f"Помилка отримання seqno: {data}")
                return 0
                
        except Exception as e:
            self.print_error(f"Не вдалося отримати seqno: {e}")
            return 0

    async def execute_batch_transfer(self, amount):
        self.print_header("ПОЧАТОК ПЕРЕКАЗІВ")
        
        successful = 0
        failed = 0
        
        for i, addr in enumerate(self.addresses, 1):
            self.print_info(f"Обробка {i}/{len(self.addresses)}: {addr}")
            
            result = await self.send_transaction(addr, amount)
            
            if result:
                self.print_success(f"✅ {addr}: {amount} TON | Hash: {result.get('hash', 'N/A')}")
                successful += 1
            else:
                self.print_error(f"❌ {addr}")
                failed += 1
                
            # Затримка між транзакціями для уникнення перевантаження
            if i < len(self.addresses):
                await asyncio.sleep(2)
                
        self.print_header("РЕЗУЛЬТАТИ")
        self.print_success(f"Успішно: {successful}")
        if failed > 0:
            self.print_error(f"Помилки: {failed}")

    async def run(self):
        self.print_colored("🚀 TON Batch Transfer 🚀", Fore.MAGENTA, Style.BRIGHT)
        
        if not self.check_dependencies():
            if not self.demo_mode:
                return
                
        if not self.setup_wallet(): 
            return
            
        if not self.load_addresses(): 
            return
            
        balance = await self.get_wallet_balance()
        if balance <= 0:
            self.print_error("Недостатньо коштів")
            return
            
        self.print_info(f"Баланс гаманця: {balance} TON")
        
        amount, mode = self.get_transfer_amount(balance)
        if not amount:
            return
            
        # Підсумок операції
        total_amount = amount * len(self.addresses)
        estimated_fees = len(self.addresses) * Decimal('0.01')
        
        self.print_header("ПІДСУМОК")
        self.print_info(f"Кількість адрес: {len(self.addresses)}")
        self.print_info(f"Сума {mode}: {amount} TON")
        self.print_info(f"Загальна сума: {total_amount} TON")
        self.print_info(f"Орієнтовні комісії: {estimated_fees} TON")
        self.print_info(f"Всього потрібно: {total_amount + estimated_fees} TON")
        
        confirm = input("\nПідтвердити переказ? (y/n): ").strip().lower()
        if confirm in ['y', 'yes', 'так']:
            await self.execute_batch_transfer(amount)
        else:
            self.print_info("Операцію скасовано")


def main():
    try:
        tool = TONBatchTransfer()
        asyncio.run(tool.run())
    except KeyboardInterrupt:
        print("\nОперацію перервано користувачем")
    except Exception as e:
        print(f"\nКритична помилка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
