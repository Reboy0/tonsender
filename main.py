#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
import sys
from typing import List, Optional, Union
from decimal import Decimal
import json
import time

# Перевірка та імпорт colorama
try:
    from colorama import Fore, Back, Style, init
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    print("Увага: colorama не встановлено. Запустіть: pip install colorama")
    COLORAMA_AVAILABLE = False
    class MockColor:
        def __getattr__(self, name):
            return ""
    Fore = Back = Style = MockColor()
    def init(**kwargs):
        pass

# Перевірка та імпорт TON SDK
TON_SDK_AVAILABLE = False
try:
    from tonsdk.provider import ToncenterClient
    from tonsdk.utils import to_nano, from_nano, Address
    from tonsdk.contract.wallet import Wallets
    from tonsdk.boc import Cell
    TON_SDK_AVAILABLE = True
except ImportError as e:
    print(f"Помилка імпорту tonsdk: {e}")
    print("\nДля встановлення виконайте:")
    print("pip install tonsdk")
    try:
        print("\nСпробуємо альтернативну бібліотеку pytonlib...")
        import pytonlib
        print("pytonlib доступний! Можна використовувати альтернативну реалізацію.")
    except ImportError:
        print("pytonlib також недоступний.")
        print("Встановіть одну з бібліотек: pip install tonsdk або pip install pytonlib")
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
        separator = "=" * 50
        if COLORAMA_AVAILABLE:
            print(f"\n{Back.BLUE}{Fore.WHITE} {text} {Style.RESET_ALL}")
        else:
            print(f"\n{separator}\n {text}\n{separator}")

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
        self.print_success("Усі необхідні залежності встановлено")
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

        try:
            self.client = ToncenterClient(
                base_url="https://toncenter.com/api/v2/",
                api_key=None
            )
            # Використання Wallets замість WalletV4R2
            from tonsdk.contract.wallet import Wallets, WalletVersionEnum
            _mn, pub_k, priv_k, wallet = Wallets.from_mnemonics(
                self.seed_phrase,
                WalletVersionEnum.v4r2,
                0
            )
            wallet.provider = self.client
            self.wallet = wallet

            address = self.wallet.address.to_string(True, True, True)
            self.print_success("Гаманець готовий!")
            self.print_info(f"Адреса: {address}")
            return True
        except Exception as e:
            self.print_error(f"Помилка ініціалізації гаманця: {e}")
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
                    Address(addr)
                    self.addresses.append(addr)
                except:
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
            wallet_address = self.wallet.address.to_string(True, True, True)
            balance = self.client.get_balance(wallet_address)
            return from_nano(int(balance))
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
                per = total / len(self.addresses)
                return Decimal(str(per)), "загальна"
            elif choice == '2':
                per = float(input("Сума на кожен адрес (TON): "))
                return Decimal(str(per)), "на кожен"
        except:
            self.print_error("Невірна сума")
        return None, None

    async def send_transaction(self, to_address: str, amount: Decimal):
        if self.demo_mode:
            await asyncio.sleep(0.1)
            return {"hash": f"demo_hash_{to_address}"}
        try:
            transfer = [{
                'address': Address(to_address),
                'amount': to_nano(amount),
                'payload': 'Batch transfer'
            }]
            boc = await self.wallet.transfer(transfer)
            result = self.client.send_boc(boc['boc'])
            return result
        except Exception as e:
            self.print_error(f"Помилка для {to_address}: {e}")
            return None

    async def execute_batch_transfer(self, amount):
        self.print_header("ПОЧАТОК ПЕРЕКАЗІВ")
        for addr in self.addresses:
            result = await self.send_transaction(addr, amount)
            if result:
                self.print_success(f"✅ {addr}: {amount} TON")
            else:
                self.print_error(f"❌ {addr}")
            await asyncio.sleep(1)

    async def run(self):
        self.print_colored("🚀 TON Batch Transfer 🚀", Fore.MAGENTA, Style.BRIGHT)
        self.check_dependencies()
        if not self.setup_wallet(): return
        if not self.load_addresses(): return
        balance = await self.get_wallet_balance()
        if balance <= 0:
            self.print_error("Недостатньо коштів")
            return
        amount, mode = self.get_transfer_amount(balance)
        if not amount:
            return
        confirm = input("Підтвердити переказ? (y/n): ").strip().lower()
        if confirm in ['y', 'yes', 'так']:
            await self.execute_batch_transfer(amount)


def main():
    try:
        tool = TONBatchTransfer()
        asyncio.run(tool.run())
    except KeyboardInterrupt:
        print("\nОперацію перервано")
    except Exception as e:
        print(f"\nКритична помилка: {e}")

if __name__ == "__main__":
    main()
