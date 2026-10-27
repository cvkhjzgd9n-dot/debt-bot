import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

# Твой токен от BotFather (вставь вместо текста ниже свой токен в кавычках)
TOKEN = "8891387008:AAEVAnjipRs0iJUY-R7ftZrtS32g6BKjmnQ"

# Твой Telegram ID
ALLOWED_USER_IDS = [850220701,1091645322]

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Данные долга
debt_data = {
    "total_debt": 1000000.0,  # 1 000 000 рублей
    "monthly_fee": 15000.0,   # 15 000 рублей ежемесячно
    "history": []             # История платежей
}

def is_allowed(user_id: int) -> bool:
    return user_id in ALLOWED_USER_IDS

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if not is_allowed(message.from_user.id):
        await message.answer("У вас нет доступа к этому боту.")
        return
    
    await message.answer(
        "Привет! Я бот для учета вашего совместного долга.\n\n"
        f"Текущий остаток долга: **{debt_data['total_debt']:,.2f} руб.**\n"
        f"Ежемесячная плата: **{debt_data['monthly_fee']:,.2f} руб.** (списывается 1 раз в календарный месяц).\n\n"
        "Просто отправь мне сумму, и я распределю её:\n"
        "• Если в этом месяце 15к еще не платили — они уйдут в ежемесячный платеж, остальное — в долг.\n"
        "• Если за этот месяц 15к уже внесли — вся сумма целиком пойдет в уменьшение долга!\n\n"
        "Команды:\n"
        "/status — узнать текущий остаток\n"
        "/history — история всех платежей\n"
        "/undo — отменить последний платеж",
        parse_mode="Markdown"
    )

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    if not is_allowed(message.from_user.id):
        return
    
    await message.answer(
        f"📊 **Текущее состояние:**\n"
        f"Остаток долга: **{debt_data['total_debt']:,.2f} руб.**\n"
        f"Ежемесячный платеж: {debt_data['monthly_fee']:,.0f} руб.",
        parse_mode="Markdown"
    )

@dp.message(Command("history"))
async def cmd_history(message: types.Message):
    if not is_allowed(message.from_user.id):
        return
    
    if not debt_data["history"]:
        await message.answer("История платежей пока пуста.")
        return
    
    history_text = "📜 **История платежей:**\n\n"
    for idx, item in enumerate(debt_data["history"], 1):
        history_text += (
            f"{idx}. Дата/Месяц: {item.get('month_str', '—')} | "
            f"Внесено: {item['total_paid']:,.2f} руб. "
            f"(В долг: {item['to_debt']:,.2f}, Ежемесячный: {item['to_monthly']:,.2f})\n"
        )
    
    await message.answer(history_text, parse_mode="Markdown")

@dp.message(Command("undo"))
async def cmd_undo(message: types.Message):
    if not is_allowed(message.from_user.id):
        return
    
    if not debt_data["history"]:
        await message.answer("⚠️ История платежей пуста, отменять нечего.")
        return
    
    last_payment = debt_data["history"].pop()
    debt_data["total_debt"] += last_payment["to_debt"]
    
    await message.answer(
        f"↩️ **Последний платеж отменен!**\n\n"
        f"• Возвращено в долг: **{last_payment['to_debt']:,.2f} руб.**\n"
        f"• Аннулирован платеж: {last_payment['total_paid']:,.2f} руб.\n\n"
        f"📉 **Текущий остаток долга:** {debt_data['total_debt']:,.2f} руб.",
        parse_mode="Markdown"
    )

@dp.message(F.text.regexp(r'^\d+([.,]?\d+)?$'))
async def process_payment(message: types.Message):
    if not is_allowed(message.from_user.id):
        return
    
    clean_text = message.text.replace(',', '.')
    total_paid = float(clean_text)
    
    # Получаем текущий год и месяц (например, "2026-09")
    current_month = datetime.now().strftime("%Y-%m")
    
    # Проверяем, был ли уже совершен ежемесячный платеж в этом календарном месяце
    monthly_already_paid = any(
        item.get("month") == current_month and item.get("to_monthly", 0) > 0 
        for item in debt_data["history"]
    )
    
    # Если за этот месяц 15к еще не платили, то вычитаем их. Если уже платили — вычет 0.
    monthly_deduction = 0.0 if monthly_already_paid else debt_data["monthly_fee"]
    
    # Проверка, если это самый первый платеж в месяце, а сумма меньше 15к
    if not monthly_already_paid and total_paid < monthly_deduction:
        await message.answer(
            f"⚠️ Введенная сумма ({total_paid:,.2f} руб.) меньше обязательного ежемесячного платежа ({monthly_deduction:,.2f} руб.) для этого месяца!"
        )
        return
    
    to_debt = total_paid - monthly_deduction
    debt_data["total_debt"] -= to_debt
    
    # Сохраняем в историю с привязкой к месяцу
    debt_data["history"].append({
        "total_paid": total_paid,
        "to_debt": to_debt,
        "to_monthly": monthly_deduction,
        "month": current_month,
        "month_str": datetime.now().strftime("%B %Y")  # Месяц словами для красоты
    })
    
    if monthly_deduction > 0:
        msg_note = f"• Ежемесячный платеж за этот месяц: {monthly_deduction:,.2f} руб. учтен.\n• В погашение долга: **{to_debt:,.2f} руб.**"
    else:
        msg_note = f"• Ежемесячный платеж за этот месяц **уже был совершен ранее**.\n• Вся сумма ({total_paid:,.2f} руб.) идет **целиком в погашение долга**!"

    await message.answer(
        f"✅ **Платеж принят!** ({total_paid:,.2f} руб.)\n\n"
        f"{msg_note}\n\n"
        f"📉 **Остаток долга:** {debt_data['total_debt']:,.2f} руб.",
        parse_mode="Markdown"
    )

async def set_bot_commands(bot: Bot):
    commands = [
        types.BotCommand(command="start", description="Перезапустить бота"),
        types.BotCommand(command="status", description="Текущий остаток долга"),
        types.BotCommand(command="history", description="История платежей"),
        types.BotCommand(command="undo", description="Отменить последний платеж")
    ]
    await bot.set_my_commands(commands)

async def main():
    logging.basicConfig(level=logging.INFO)
    await set_bot_commands(bot)
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

