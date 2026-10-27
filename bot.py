import asyncio
import logging
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

TOKEN = "8891387008:AAEVAnjipRs0iJUY-R7ftZrtS32g6BKjmnQ"
ALLOWED_USER_IDS = [850220701, 1091645322]

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

debt_data = {
    "total_debt": 1000000.0,
    "monthly_fee": 15000.0,
    "history": []
}

def is_allowed(user_id: int) -> bool:
    return user_id in ALLOWED_USER_IDS

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if not is_allowed(message.from_user.id):
        return
    await message.answer(
        "Привет! Я бот для учета вашего совместного долга.\n\n"
        f"Текущий остаток долга: **{debt_data['total_debt']:,.2f} руб.**\n"
        f"Ежемесячная плата: **{debt_data['monthly_fee']:,.2f} руб.**\n\n"
        "Команды:\n/status — остаток\n/history — история\n/undo — отмена",
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
            f"{idx}. {item.get('month_str', '—')} | "
            f"Внесено: {item['total_paid']:,.2f} руб. "
            f"(В долг: {item['to_debt']:,.2f}, Ежемес: {item['to_monthly']:,.2f})\n"
        )
    await message.answer(history_text, parse_mode="Markdown")

@dp.message(Command("undo"))
async def cmd_undo(message: types.Message):
    if not is_allowed(message.from_user.id):
        return
    if not debt_data["history"]:
        await message.answer("⚠️ История пуста, отменять нечего.")
        return
    last_payment = debt_data["history"].pop()
    debt_data["total_debt"] += last_payment["to_debt"]
    await message.answer(
        f"↩️ **Последний платеж отменен!**\n"
        f"📉 **Остаток долга:** {debt_data['total_debt']:,.2f} руб.",
        parse_mode="Markdown"
    )
@dp.message(F.text.regexp(r'^\d+([.,]?\d+)?$'))
async def process_payment(message: types.Message):
    if not is_allowed(message.from_user.id):
        return
    total_paid = float(message.text.replace(',', '.'))
    current_month = datetime.now().strftime("%Y-%m")
    monthly_already_paid = any(
        item.get("month") == current_month and item.get("to_monthly", 0) > 0 
        for item in debt_data["history"]
    )
    monthly_deduction = 0.0 if monthly_already_paid else debt_data["monthly_fee"]
    if not monthly_already_paid and total_paid < monthly_deduction:
        await message.answer(
            f"⚠️ Сумма ({total_paid:,.2f} руб.) меньше обязательного платежа ({monthly_deduction:,.2f} руб.)!"
        )
        return
    to_debt = total_paid - monthly_deduction
    debt_data["total_debt"] -= to_debt
    debt_data["history"].append({
        "total_paid": total_paid,
        "to_debt": to_debt,
        "to_monthly": monthly_deduction,
        "month": current_month,
        "month_str": datetime.now().strftime("%B %Y")
    })
    if monthly_deduction > 0:
        msg_note = f"• Ежемесячный платеж: {monthly_deduction:,.2f} руб. учтен.\n• В погашение долга: **{to_debt:,.2f} руб.**"
    else:
        msg_note = f"• Ежемесячный платеж уже был внесен ранее.\n• Вся сумма ({total_paid:,.2f} руб.) идет **в погашение долга**!"
    await message.answer(
        f"✅ **Платеж принят!** ({total_paid:,.2f} руб.)\n\n{msg_note}\n\n"
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

async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    logging.basicConfig(level=logging.INFO)
    await set_bot_commands(bot)
    await start_web_server()
    print("Бот и веб-сервер запущены...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
