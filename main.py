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
    # Заглушки для кольорів
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
    from tonsdk.contract.wallet import Wallet, WalletVersionEnum
    from tonsdk.crypto import mnemonic_new, mnemonic_to_wallet_key
    from tonsdk.boc import Cell
    TON_SDK_AVAILABLE = True
except ImportError as e:
    print(f"Помилка імпорту tonsdk: {e}")
    print("\nДля встановлення виконайте:")
    print("pip install tonsdk")
    print("або")
    print("pip install tonsdk==1.0.19")
    
    # Альтернативний варіант - спробуємо pytonlib
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
        """Виводить повідомлення з кольором"""
        if COLORAMA_AVAILABLE:
            print(f"{style}{color}{message}{Style.RESET_ALL}")
        else:
            print(message)
        
    def print_header(self, text: str):
        """Виводить заголовок"""
        separator = "=" * 50
        if COLORAMA_AVAILABLE:
            print(f"\n{Back.BLUE}{Fore.WHITE} {text} {Style.RESET_ALL}")
        else:
            print(f"\n{separator}")
            print(f" {text}")
            print(separator)
        
    def print_success(self, text: str):
        """Виводить повідомлення про успіх"""
        self.print_colored(f"✅ {text}", Fore.GREEN, Style.BRIGHT)
        
    def print_error(self, text: str):
        """Виводить повідомлення про помилку"""
        self.print_colored(f"❌ {text}", Fore.RED, Style.BRIGHT)
        
    def print_warning(self, text: str):
        """Виводить попередження"""
        self.print_colored(f"⚠️  {text}", Fore.YELLOW, Style.BRIGHT)
        
    def print_info(self, text: str):
        """Виводить інформаційне повідомлення"""
        self.print_colored(f"ℹ️  {text}", Fore.CYAN)
        
    def check_dependencies(self):
        """Перевірка залежностей"""
        self.print_header("ПЕРЕВІРКА ЗАЛЕЖНОСТЕЙ")
        
        if not TON_SDK_AVAILABLE:
            self.print_error("TON SDK не встановлено!")
            self.print_warning("Запуск у демо-режимі...")
            self.demo_mode = True
            return False
            
        if not COLORAMA_AVAILABLE:
            self.print_warning("Colorama не встановлено, використовуємо базовий вивід")
            
        self.print_success("Усі необхідні залежності встановлено")
        return True
        
    def setup_wallet(self):
        """Налаштування гаманця"""
        self.print_header("НАЛАШТУВАННЯ ГАМАНЦЯ")
        
        if self.demo_mode:
            self.print_warning("Демо-режим: імітація налаштування гаманця")
            self.seed_phrase = ["demo"] * 24
            return True
        
        # Вибір способу введення seed фрази
        self.print_colored("Оберіть спосіб введення seed фрази:", Fore.YELLOW)
        print("1. Ввести вручну в консолі")
        print("2. Зчитати з файлу")
        
        choice = input(f"Ваш вибір (1 або 2): ").strip()
        
        if choice == "1":
            # Введення seed фрази вручну
            seed_input = input("Введіть вашу seed фразу (24 слова через пробіл): ").strip()
            self.seed_phrase = seed_input.split()
        elif choice == "2":
            # Зчитування з файлу
            seed_file = input("Введіть назву файлу з seed фразою: ").strip()
            try:
                with open(seed_file, 'r', encoding='utf-8') as f:
                    self.seed_phrase = f.read().strip().split()
                self.print_success(f"Seed фразу зчитано з файлу {seed_file}")
            except Exception as e:
                self.print_error(f"Помилка читання файлу: {e}")
                return False
        else:
            self.print_error("Невірний вибір!")
            return False
        
        if len(self.seed_phrase) != 24:
            self.print_error(f"Seed фраза повинна містити 24 слова! Знайдено: {len(self.seed_phrase)}")
            return False
            
        # Ініціалізація клієнта TON
        try:
            self.client = ToncenterClient(
                base_url="https://toncenter.com/api/v2/",
                api_key=None  # Можна додати API ключ для кращої продуктивності
            )
            
            # Створення гаманця - ВИПРАВЛЕНА ЧАСТИНА
            private_key, public_key = mnemonic_to_wallet_key(self.seed_phrase)
            self.wallet = Wallet(version='v4r2', public_key=public_key, private_key=private_key)
            
            # Отримання адреси гаманця
            wallet_address = self.wallet.address.to_string(True, True, True)
            self.print_success("Гаманець успішно ініціалізовано!")
            self.print_info(f"Адреса гаманця: {wallet_address}")
            return True
        except Exception as e:
            self.print_error(f"Помилка ініціалізації гаманця: {e}")
            return False
            
    def load_addresses(self):
        """Завантаження адрес з файлу"""
        self.print_header("ЗАВАНТАЖЕННЯ АДРЕС")
        
        filename = input("Введіть назву файлу з адресами (txt): ").strip()
        
        if not os.path.exists(filename):
            self.print_error(f"Файл {filename} не знайдено!")
            
            # Пропонуємо створити тестовий файл
            create_test = input("Створити тестовий файл з адресами? (y/n): ").strip().lower()
            if create_test == 'y':
                return self.create_test_addresses_file(filename)
            return False
            
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                raw_addresses = [line.strip() for line in f.readlines() if line.strip()]
            
            if self.demo_mode:
                # У демо-режимі приймаємо будь-які адреси
                self.addresses = raw_addresses
                self.print_success(f"Завантажено {len(self.addresses)} адрес (демо-режим)")
                return True
            
            # Валідація адрес
            valid_addresses = []
            for addr in raw_addresses:
                try:
                    # Перевіряємо чи адреса валідна
                    Address(addr)
                    valid_addresses.append(addr)
                except:
                    self.print_warning(f"Пропущено невалідну адресу: {addr}")
            
            self.addresses = valid_addresses
                
            if not self.addresses:
                self.print_error("Файл не містить валідних адрес!")
                return False
                
            self.print_success(f"Завантажено {len(self.addresses)} валідних адрес")
            for i, addr in enumerate(self.addresses[:5], 1):  # Показуємо тільки перші 5
                self.print_info(f"{i}. {addr}")
            
            if len(self.addresses) > 5:
                self.print_info(f"... та ще {len(self.addresses) - 5} адрес")
                
            return True
        except Exception as e:
            self.print_error(f"Помилка читання файлу: {e}")
            return False
            
    def create_test_addresses_file(self, filename: str):
        """Створення тестового файлу з адресами"""
        test_addresses = [
            "EQD7zbVznJ_z7MqCmMLa42RKw1A9bGjNLjGdlGhDUKrNqNhI",
            "EQC5zTFhHwMNFUiONQzYhHy1H8j4EbGqaZp9QKxpH7j5WUhJ",
            "EQB7zbVznJ_z7MqCmMLa42RKw1A9bGjNLjGdlGhDUKrNqNhI"
        ]
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for addr in test_addresses:
                    f.write(addr + '\n')
            
            self.print_success(f"Створено тестовий файл {filename}")
            self.addresses = test_addresses
            return True
        except Exception as e:
            self.print_error(f"Помилка створення файлу: {e}")
            return False
            
    async def get_wallet_balance(self):
        """Отримання балансу гаманця"""
        if self.demo_mode:
            return Decimal('10.5')  # Демо-баланс
            
        try:
            # Отримуємо адресу гаманця
            wallet_address = self.wallet.address.to_string(True, True, True)
            
            # Отримуємо баланс через клієнт
            balance_info = await self.client.get_balance(wallet_address)
            
            # balance_info може бути числом або словником
            if isinstance(balance_info, dict):
                balance = int(balance_info.get('result', 0))
            else:
                balance = int(balance_info)
                
            return from_nano(balance)
        except Exception as e:
            self.print_error(f"Помилка отримання балансу: {e}")
            return Decimal('0')
            
    def get_transfer_amount(self, balance: Decimal):
        """Отримання суми для переказу"""
        self.print_header("ВИБІР СУМИ ДЛЯ ПЕРЕКАЗУ")
        self.print_info(f"Поточний баланс: {balance} TON")
        
        self.print_colored("Оберіть тип переказу:", Fore.YELLOW)
        print("1. Загальна сума (розподілити між усіма адресами)")
        print("2. Сума на кожен адрес")
        
        choice = input("Ваш вибір (1 або 2): ").strip()
        
        try:
            if choice == "1":
                total_amount = float(input("Введіть загальну суму TON: "))
                if total_amount <= 0:
                    self.print_error("Сума повинна бути більша за 0!")
                    return None, None
                    
                amount_per_address = total_amount / len(self.addresses)
                self.print_info(f"Сума на кожен адрес: {amount_per_address:.6f} TON")
                return Decimal(str(amount_per_address)), "загальна"
                
            elif choice == "2":
                amount_per_address = float(input("Введіть суму TON на кожен адрес: "))
                if amount_per_address <= 0:
                    self.print_error("Сума повинна бути більша за 0!")
                    return None, None
                    
                total_amount = amount_per_address * len(self.addresses)
                self.print_info(f"Загальна сума: {total_amount:.6f} TON")
                return Decimal(str(amount_per_address)), "на кожен"
                
            else:
                self.print_error("Невірний вибір!")
                return None, None
        except ValueError:
            self.print_error("Невірний формат суми!")
            return None, None
            
    async def estimate_fees(self, amount_per_address: Decimal):
        """Оцінка комісій"""
        try:
            # Приблизна комісія за одну транзакцію в TON
            fee_per_tx = Decimal("0.01")  # ~0.01 TON за транзакцію
            total_fees = fee_per_tx * len(self.addresses)
            
            self.print_info(f"Орієнтовна комісія за транзакцію: {fee_per_tx} TON")
            self.print_info(f"Загальна орієнтовна комісія: {total_fees} TON")
            
            return total_fees
        except Exception as e:
            self.print_error(f"Помилка оцінки комісій: {e}")
            return Decimal("0.05")  # Резервна оцінка
            
    async def send_transaction(self, to_address: str, amount: Decimal):
        """Відправлення транзакції"""
        if self.demo_mode:
            # Імітація відправлення транзакції
            await asyncio.sleep(0.1)  # Імітація затримки
            return {"hash": f"demo_tx_{hash(to_address)}", "success": True}
            
        try:
            # Створення тіла транзакції
            body = Cell()
            body.bits.write_uint(0, 32)  # op code для простого переказу
            body.bits.write_string("Batch transfer")  # коментар
            
            # Відправлення через гаманець
            query = self.wallet.create_transfer_message(
                to_addr=Address(to_address),
                amount=to_nano(amount),
                payload=body,
                state_init=None,
                send_mode=3
            )
            
            # Відправка транзакції
            result = await self.client.raw_send_message(query['message'].to_boc(False))
            
            return {
                "hash": result['result'],
                "success": True
            }
        except Exception as e:
            raise Exception(f"Помилка відправлення: {e}")
            
    async def execute_batch_transfer(self, amount_per_address: Decimal):
        """Виконання масового переказу"""
        self.print_header("ВИКОНАННЯ ПЕРЕКАЗІВ")
        
        if self.demo_mode:
            self.print_warning("Демо-режим: імітація переказів")
        
        successful_transfers = 0
        failed_transfers = 0
        total_sent = Decimal('0')
        
        for i, address in enumerate(self.addresses, 1):
            self.print_info(f"Обробка {i}/{len(self.addresses)}: {address}")
            
            try:
                # Відправлення транзакції
                result = await self.send_transaction(address, amount_per_address)
                
                if result and result.get('success'):
                    self.print_success(f"Переказ на {address}: {amount_per_address} TON")
                    self.print_info(f"   Хеш: {result.get('hash')}")
                    successful_transfers += 1
                    total_sent += amount_per_address
                else:
                    self.print_error(f"Невдалий переказ на {address}")
                    failed_transfers += 1
                    
            except Exception as e:
                self.print_error(f"Помилка переказу на {address}: {e}")
                failed_transfers += 1
                
            # Пауза між транзакціями
            if i < len(self.addresses):
                delay = 2 if self.demo_mode else 5
                self.print_info(f"Очікування {delay} секунд...")
                await asyncio.sleep(delay)
                
        # Підсумок
        self.print_header("ПІДСУМОК ОПЕРАЦІЙ")
        self.print_success(f"Успішних переказів: {successful_transfers}")
        self.print_success(f"Загальна сума відправлена: {total_sent} TON")
        if failed_transfers > 0:
            self.print_error(f"Невдалих переказів: {failed_transfers}")
        self.print_info(f"Загалом оброблено: {len(self.addresses)} адрес")
        
    async def run(self):
        """Основна функція запуску"""
        self.print_colored("🚀 TON BATCH TRANSFER TOOL 🚀", Fore.MAGENTA, Style.BRIGHT)
        self.print_colored("=" * 50, Fore.MAGENTA)
        
        # Перевірка залежностей
        self.check_dependencies()
        
        # Налаштування гаманця
        if not self.setup_wallet():
            return
            
        # Завантаження адрес
        if not self.load_addresses():
            return
            
        # Отримання балансу
        self.print_header("ПЕРЕВІРКА БАЛАНСУ")
        self.print_info("Отримання балансу гаманця...")
        balance = await self.get_wallet_balance()
        
        if balance <= 0:
            self.print_error("Недостатньо коштів на гаманці!")
            return
            
        # Вибір суми
        amount_per_address, transfer_type = self.get_transfer_amount(balance)
        if not amount_per_address:
            return
            
        # Оцінка комісій
        estimated_fees = await self.estimate_fees(amount_per_address)
        total_needed = (amount_per_address * len(self.addresses)) + estimated_fees
        
        # Підтвердження операції
        self.print_header("ПІДТВЕРДЖЕННЯ ОПЕРАЦІЇ")
        self.print_info(f"Адрес для переказу: {len(self.addresses)}")
        self.print_info(f"Сума {transfer_type}: {amount_per_address} TON")
        self.print_info(f"Загальна сума переказів: {amount_per_address * len(self.addresses)} TON")
        self.print_info(f"Орієнтовні комісії: {estimated_fees} TON")
        self.print_info(f"Загалом потрібно: {total_needed} TON")
        self.print_info(f"Доступно: {balance} TON")
        
        if total_needed > balance and not self.demo_mode:
            self.print_error("Недостатньо коштів для виконання всіх переказів!")
            self.print_warning(f"Потрібно додатково: {total_needed - balance} TON")
            return
            
        # Підтвердження
        print(f"\n{'='*50}")
        if self.demo_mode:
            self.print_warning("ДЕМО-РЕЖИМ: Реальні транзакції не будуть виконані")
        else:
            self.print_warning("УВАГА: Операція незворотна!")
        print(f"{'='*50}")
        
        confirm = input(f"\nПідтвердити виконання переказів? (так/yes/y): ").strip().lower()
        
        if confirm in ['так', 'yes', 'y', 'да']:
            await self.execute_batch_transfer(amount_per_address)
        else:
            self.print_warning("Операцію скасовано користувачем.")

def main():
    """Головна функція"""
    try:
        transfer_tool = TONBatchTransfer()
        asyncio.run(transfer_tool.run())
        
    except KeyboardInterrupt:
        print(f"\nОперацію перервано користувачем (Ctrl+C).")
    except Exception as e:
        print(f"\nКритична помилка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
