import asyncio
from pytoniq_core import Address
from pytoniq import LiteBalancer, WalletV4R2
import sys
import os

# Функції для конвертації одиниць TON
def to_nano(ton_amount):
    """Конвертує TON в nanoTON"""
    return int(ton_amount * 1_000_000_000)

def from_nano(nano_amount):
    """Конвертує nanoTON в TON"""
    return nano_amount / 1_000_000_000

async def main():
    # Перевіряємо наявність файлів
    if not os.path.exists("seed.txt"):
        print("❌ Файл seed.txt не знайдено!")
        sys.exit(1)
    
    if not os.path.exists("wallets.txt"):
        print("❌ Файл wallets.txt не знайдено!")
        sys.exit(1)
    
    # Зчитуємо seed-фразу
    try:
        with open("seed.txt", "r", encoding="utf-8") as f:
            mnemonic = f.read().strip().split()
            
        if len(mnemonic) not in [12, 24]:
            print("❌ Seed-фраза повинна містити 12 або 24 слова!")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Помилка читання seed.txt: {e}")
        sys.exit(1)
    
    # Зчитуємо список адрес
    try:
        with open("wallets.txt", "r", encoding="utf-8") as f:
            addresses = [line.strip() for line in f if line.strip()]
            
        if not addresses:
            print("❌ Файл wallets.txt порожній або не містить валідних адрес!")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Помилка читання wallets.txt: {e}")
        sys.exit(1)
    
    # Отримуємо дані від користувача
    try:
        amount = float(input("Скільки TON надсилати кожному? "))
        if amount <= 0:
            print("❌ Сума повинна бути більше 0!")
            sys.exit(1)
    except ValueError:
        print("❌ Невірний формат суми!")
        sys.exit(1)
    
    comment = input("Коментар (необов'язково): ").strip()
    
    # Показуємо інформацію про операцію
    print(f"\n📋 Буде надіслано {amount} TON до {len(addresses)} адрес")
    print(f"💰 Загальна сума: {amount * len(addresses)} TON")
    
    confirm = input("Продовжити? (y/N): ").strip().lower()
    if confirm != 'y' and confirm != 'yes':
        print("❌ Операцію скасовано")
        sys.exit(0)
    
    # Ініціалізуємо клієнт
    client = None
    try:
        # Створюємо підключення до TON
        client = LiteBalancer.from_mainnet_config(trust_level=2)
        await client.start_up()
        
        # Створюємо гаманець з мнемонічної фрази
        wallet = await WalletV4R2.from_mnemonic(client, mnemonic)
        
        # Отримуємо адресу гаманця
        address = wallet.address
        print(f"\n🔑 Ваш гаманець: {address.to_str()}")
        
        # Перевіряємо баланс
        balance = await wallet.get_balance()
        balance_ton = from_nano(balance)
        print(f"💳 Баланс: {balance_ton:.6f} TON")
        
        # Перевіряємо чи достатньо коштів
        total_needed = amount * len(addresses)
        if balance_ton < total_needed:
            print(f"❌ Недостатньо коштів! Потрібно: {total_needed} TON, є: {balance_ton:.6f} TON")
            return
        
        # Надсилаємо транзакції
        successful = 0
        failed = 0
        
        for i, dest_addr in enumerate(addresses, 1):
            try:
                print(f"📤 [{i}/{len(addresses)}] Надсилаємо до {dest_addr}...")
                
                # Додаємо невелику затримку між транзакціями
                if i > 1:
                    await asyncio.sleep(3)
                
                # Створюємо адресу отримувача
                destination = Address(dest_addr)
                
                # Надсилаємо транзакцію
                result = await wallet.transfer(
                    destination=destination,
                    amount=to_nano(amount),
                    body=comment if comment else ""
                )
                
                print(f"✅ Успішно надіслано {amount} TON до {dest_addr}")
                successful += 1
                
            except Exception as e:
                print(f"❌ Помилка для {dest_addr}: {e}")
                failed += 1
                
                # Можна вибрати: продовжувати чи зупинитися
                if input("Продовжити з наступною адресою? (y/N): ").strip().lower() not in ['y', 'yes']:
                    break
        
        print(f"\n📊 Результати:")
        print(f"✅ Успішно: {successful}")
        print(f"❌ Помилок: {failed}")
        
    except Exception as e:
        print(f"❌ Критична помилка: {e}")
        
    finally:
        if client:
            await client.close_all()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Операцію перервано користувачем")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Неочікувана помилка: {e}")
        sys.exit(1)
