
import asyncio
from pytoniq_core import Address
from pytoniq import LiteBalancer, WalletV4R2
import sys
import os

# Colorama для красивого виводу
try:
    from colorama import Fore, Back, Style, init
    init(autoreset=True)
    COLORAMA = True
except ImportError:
    COLORAMA = False
    class Dummy:
        def __getattr__(self, name): return ""
    Fore = Back = Style = Dummy()

# Функції для конвертації одиниць TON

def to_nano(ton_amount):
    """Конвертує TON в nanoTON"""
    return int(ton_amount * 1_000_000_000)

def from_nano(nano_amount):
    """Конвертує nanoTON в TON"""
    return nano_amount / 1_000_000_000

def print_header(text):
    if COLORAMA:
        print(f"\n{Back.BLUE}{Fore.WHITE}{Style.BRIGHT} {text} {Style.RESET_ALL}")
    else:
        print(f"\n{'='*50}\n{text}\n{'='*50}")

def print_success(text):
    if COLORAMA:
        print(f"{Fore.GREEN}{Style.BRIGHT}✅ {text}{Style.RESET_ALL}")
    else:
        print(f"✅ {text}")

def print_error(text):
    if COLORAMA:
        print(f"{Fore.RED}{Style.BRIGHT}❌ {text}{Style.RESET_ALL}")
    else:
        print(f"❌ {text}")

def print_warning(text):
    if COLORAMA:
        print(f"{Fore.YELLOW}{Style.BRIGHT}⚠️  {text}{Style.RESET_ALL}")
    else:
        print(f"⚠️  {text}")

def print_info(text):
    if COLORAMA:
        print(f"{Fore.CYAN}ℹ️  {text}{Style.RESET_ALL}")
    else:
        print(f"ℹ️  {text}")

async def main():
    # Перевіряємо наявність файлів
    if not os.path.exists("seed.txt"):
        print_error("Файл seed.txt не знайдено!")
        sys.exit(1)
    if not os.path.exists("wallets.txt"):
        print_error("Файл wallets.txt не знайдено!")
        sys.exit(1)
    
    # Зчитуємо seed-фразу
    try:
        with open("seed.txt", "r", encoding="utf-8") as f:
            mnemonic = f.read().strip().split()
        if len(mnemonic) not in [12, 24]:
            print_error("Seed-фраза повинна містити 12 або 24 слова!")
            sys.exit(1)
    except Exception as e:
        print_error(f"Помилка читання seed.txt: {e}")
        sys.exit(1)
    
    # Зчитуємо список адрес
    try:
        with open("wallets.txt", "r", encoding="utf-8") as f:
            addresses = [line.strip() for line in f if line.strip()]
        if not addresses:
            print_error("Файл wallets.txt порожній або не містить валідних адрес!")
            sys.exit(1)
    except Exception as e:
        print_error(f"Помилка читання wallets.txt: {e}")
        sys.exit(1)
    
    # Вивід кількості гаманців і балансу перед введенням суми
    print_header("ІНФОРМАЦІЯ ПРО ГАМАНЕЦЬ")
    print_info(f"Кількість адрес для розсилки: {len(addresses)}")
    # Показати баланс (отримати його, якщо ще не отримано)
    # Якщо balance_ton ще не визначено, отримати його
    if 'balance_ton' not in locals():
        try:
            client_tmp = LiteBalancer.from_mainnet_config(trust_level=2)
            await client_tmp.start_up()
            wallet_tmp = await WalletV4R2.from_mnemonic(client_tmp, mnemonic)
            balance = await wallet_tmp.get_balance()
            balance_ton = from_nano(balance)
            await client_tmp.close_all()
        except Exception as e:
            print_warning(f"Не вдалося отримати баланс: {e}")
            balance_ton = 0
    print_info(f"Поточний баланс: {balance_ton:.6f} TON")

    # Отримуємо дані від користувача
    try:
        amount = float(input(f"{Fore.YELLOW if COLORAMA else ''}Скільки TON надсилати кожному? {Style.RESET_ALL if COLORAMA else ''}"))
        if amount <= 0:
            print_error("Сума повинна бути більше 0!")
            sys.exit(1)
    except ValueError:
        print_error("Невірний формат суми!")
        sys.exit(1)

    comment = input(f"{Fore.YELLOW if COLORAMA else ''}Коментар (необов'язково): {Style.RESET_ALL if COLORAMA else ''}").strip()

    print_header("ПІДТВЕРДЖЕННЯ ОПЕРАЦІЇ")
    print_info(f"Буде надіслано {amount} TON до {len(addresses)} адрес")
    print_info(f"Загальна сума: {amount * len(addresses)} TON")
    if comment:
        print_info(f"Коментар: {comment}")

    confirm = input(f"{Fore.YELLOW if COLORAMA else ''}Продовжити? (y/N): {Style.RESET_ALL if COLORAMA else ''}").strip().lower()
    if confirm not in ['y', 'yes']:
        print_error("Операцію скасовано")
        sys.exit(0)
    
    # Ініціалізуємо клієнт
    client = None
    try:
        print_header("ПІДКЛЮЧЕННЯ ДО TON")
        client = LiteBalancer.from_mainnet_config(trust_level=2)
        await client.start_up()
        wallet = await WalletV4R2.from_mnemonic(client, mnemonic)
        address = wallet.address
        print_success(f"Ваш гаманець: {address.to_str()}")
        balance = await wallet.get_balance()
        balance_ton = from_nano(balance)
        print_success(f"Баланс: {balance_ton:.6f} TON")
        total_needed = amount * len(addresses)
        if balance_ton < total_needed:
            print_error(f"Недостатньо коштів! Потрібно: {total_needed} TON, є: {balance_ton:.6f} TON")
            return
        print_header("ВІДПРАВКА ТРАНЗАКЦІЙ")
        successful = 0
        failed = 0
        for i, dest_addr in enumerate(addresses, 1):
            try:
                print_info(f"[{i}/{len(addresses)}] Надсилаємо до {dest_addr}...")
                if i > 1:
                    await asyncio.sleep(3)
                destination = Address(dest_addr)
                result = await wallet.transfer(
                    destination=destination,
                    amount=to_nano(amount),
                    body=comment if comment else ""
                )
                print_success(f"Успішно надіслано {amount} TON до {dest_addr}")
                successful += 1
            except Exception as e:
                print_error(f"Помилка для {dest_addr}: {e}")
                failed += 1
                if input(f"{Fore.YELLOW if COLORAMA else ''}Продовжити з наступною адресою? (y/N): {Style.RESET_ALL if COLORAMA else ''}").strip().lower() not in ['y', 'yes']:
                    break
        print_header("РЕЗУЛЬТАТИ")
        print_success(f"Успішно: {successful}")
        if failed:
            print_error(f"Помилок: {failed}")
    except Exception as e:
        print_error(f"Критична помилка: {e}")
    finally:
        if client:
            await client.close_all()

if __name__ == "__main__":
    try:
        print_header("🚀 TON Batch Transfer 🚀")
        asyncio.run(main())
    except KeyboardInterrupt:
        print_error("Операцію перервано користувачем")
        sys.exit(0)
    except Exception as e:
        print_error(f"Неочікувана помилка: {e}")
        sys.exit(1)
