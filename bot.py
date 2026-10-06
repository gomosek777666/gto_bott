import asyncio
import logging
from datetime import datetime
import os
from aiohttp import web

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Укажи здесь токен своего бота из @BotFather
TOKEN = "8918149877:AAHSbSw8_YK96NuVIUmO7zriBFpmcJSCsNQ"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Временное хранилище прогресса пользователей (в памяти)
# Формат: {user_id: [{"exercise": "Отжимания", "count": 25, "date": "06.10.2026"}, ...]}
user_progress = {}


# === Состояния FSM ===
class TrainingPlan(StatesGroup):
    waiting_for_days = State()
    waiting_for_level = State()


class ProgressState(StatesGroup):
    waiting_for_exercise = State()
    waiting_for_count = State()


# === Главное меню ===
def main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🏆 Нормативы ГТО (6 ступень)"),
                KeyboardButton(text="💪 Комплекс ОФП"),
            ],
            [
                KeyboardButton(text="📅 Индивидуальный план"),
                KeyboardButton(text="📊 Дневник прогресса"),
            ],
        ],
        resize_keyboard=True,
    )
    return keyboard


# === Обработчик команды /start ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я бот для подготовки к сдаче нормативов ГТО (6 ступень, 16-17 лет) и фиксации твоего спортивного прогресса.\n\n"
        "Выбери нужный раздел в меню ниже:",
        reply_markup=main_keyboard(),
    )


# === Раздел: Нормативы ГТО ===
@dp.message(F.text == "🏆 Нормативы ГТО (6 ступень)")
async def gto_standards(message: types.Message):
    text = (
        "🥇 Основные нормативы ГТО (6 ступень — Золотой знак):\n\n"
        "🏃 Юноши (16-17 лет):\n"
        "• Бег 60 м: 7.9 сек\n"
        "• Бег 3000 м: 12:20 мин\n"
        "• Подтягивания на высокой перекладине: 13 раз\n"
        "• Наклон вперед из положения стоя: +13 см\n"
        "• Прыжок в длину с места: 230 см\n\n"
        "🏃‍♀️ Девушки (16-17 лет):\n"
        "• Бег 60 м: 9.7 сек\n"
        "• Бег 2000 м: 10:15 мин\n"
        "• Сгибание и разгибание рук (отжимания): 17 раз\n"
        "• Наклон вперед из положения стоя: +16 см\n"
        "• Прыжок в длину с места: 185 см"
    )
    await message.answer(text, parse_mode="Markdown")


# === Раздел: Комплекс ОФП ===
@dp.message(F.text == "💪 Комплекс ОФП")
async def ofp_complex(message: types.Message):
    text = (
        "🏋️ Базовый комплекс ОФП на все группы мышц:\n\n"
        "1. Разминка (5-7 мин): суставная гимнастика, легкий бег на месте.\n"
        "2. Отжимания: 3 подхода по 15-20 раз (грудь и трицепс).\n"
        "3. Приседания: 3 подхода по 25-30 раз (ноги и ягодицы).\n"
        "4. Планка: 3 подхода по 45-60 секунд (мышцы кора).\n"
        "5. Скручивания на пресс: 3 подхода по 20 раз.\n"
        "6. Заминка: растяжка основных групп мышц."
    )
    await message.answer(text, parse_mode="Markdown")


# === Раздел: Индивидуальный план ===
@dp.message(F.text == "📅 Индивидуальный план")
async def start_plan(message: types.Message, state: FSMContext):
    await state.set_state(TrainingPlan.waiting_for_days)
    await message.answer(
        "Сколько дней в неделю ты готов тренироваться? (Введи число от 2 до 5):",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(TrainingPlan.waiting_for_days)
async def process_days(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or not (2 <= int(message.text) <= 5):
        await message.answer("Пожалуйста, введи число от 2 до 5.")
        return

    await state.update_data(days=int(message.text))
    await state.set_state(TrainingPlan.waiting_for_level)
level_kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Начальный"),
                KeyboardButton(text="Средний"),
                KeyboardButton(text="Продвинутый"),
            ]
        ],
        resize_keyboard=True,
    )
    await message.answer(
        "Выбери свой уровень физической подготовки:", reply_markup=level_kb
    )


@dp.message(TrainingPlan.waiting_for_level)
async def process_level(message: types.Message, state: FSMContext):
    if message.text not in ["Начальный", "Средний", "Продвинутый"]:
        await message.answer("Пожалуйста, выбери вариант с помощью кнопок.")
        return

    user_data = await state.get_data()
    days = user_data["days"]
    level = message.text

    plan_text = (
        f"✅ Твой план тренировок составлен!\n\n"
        f"• Количество тренировок: {days} раза в неделю\n"
        f"• Уровень: {level}\n\n"
        f"Рекомендации:\n"
        f"• Чередуй дни тренировок с днями отдыха.\n"
        f"• Не забудь записывать свои результаты в раздел «📊 Дневник прогресса»!"
    )

    await state.clear()
    await message.answer(
        plan_text, reply_markup=main_keyboard(), parse_mode="Markdown"
    )


# === Раздел: Дневник прогресса ===
@dp.message(F.text == "📊 Дневник прогресса")
async def progress_menu(message: types.Message):
    progress_kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="➕ Записать подход"),
                KeyboardButton(text="📈 Мой прогресс"),
            ],
            [KeyboardButton(text="⬅️ В главное меню")],
        ],
        resize_keyboard=True,
    )
    await message.answer("Выбери действие:", reply_markup=progress_kb)


@dp.message(F.text == "⬅️ В главное меню")
async def back_to_main(message: types.Message):
    await message.answer("Главное меню:", reply_markup=main_keyboard())


# === Ввод нового результата ===
@dp.message(F.text == "➕ Записать подход")
async def start_add_progress(message: types.Message, state: FSMContext):
    await state.set_state(ProgressState.waiting_for_exercise)

    exercises_kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Отжимания"),
                KeyboardButton(text="Подтягивания"),
            ],
            [KeyboardButton(text="Пресс"), KeyboardButton(text="Приседания")],
        ],
        resize_keyboard=True,
    )
    await message.answer("Выбери упражнение:", reply_markup=exercises_kb)


@dp.message(ProgressState.waiting_for_exercise)
async def process_exercise(message: types.Message, state: FSMContext):
    if message.text not in [
        "Отжимания",
        "Подтягивания",
        "Пресс",
        "Приседания",
    ]:
        await message.answer("Пожалуйста, выбери упражнение из списка на кнопках.")
        return

    await state.update_data(exercise=message.text)
    await state.set_state(ProgressState.waiting_for_count)
    await message.answer(
        f"Сколько повторений ({message.text.lower()}) ты сделал? (Введи только число):",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(ProgressState.waiting_for_count)
async def process_count(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) <= 0:
        await message.answer("Пожалуйста, введи положительное число.")
        return

    user_data = await state.get_data()
    exercise = user_data["exercise"]
    count = int(message.text)
    user_id = message.from_user.id
    date_str = datetime.now().strftime("%d.%m.%Y")

    if user_id not in user_progress:
        user_progress[user_id] = []

    user_progress[user_id].append(
        {"exercise": exercise, "count": count, "date": date_str}
    )

    await state.clear()

    progress_kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="➕ Записать подход"),
                KeyboardButton(text="📈 Мой прогресс"),
            ],
            [KeyboardButton(text="⬅️️ В главное меню")],
        ],
        resize_keyboard=True,
    )
await message.answer(
        f"🎉 Записано! {exercise}: {count} повторений ({date_str}).\nОтличная работа!",
        reply_markup=progress_kb,
        parse_mode="Markdown",
    )


# === Просмотр всей истории и прогресса ===
@dp.message(F.text == "📈 Мой прогресс")
async def show_progress(message: types.Message):
    user_id = message.from_user.id
    records = user_progress.get(user_id, [])

    if not records:
        await message.answer(
            "У тебя пока нет записанных тренировок.\nНажми «➕ Записать подход», чтобы добавить первое достижение!",
            parse_mode="Markdown",
        )
        return

    text = "📋 Твой спортивный дневник:\n\n"
    # Показываем последние 10 записей
    for item in records[-10:]:
        text += (
            f"• {item['date']} — {item['exercise']}: {item['count']} раз\n"
        )

    text += "\nПродолжай в том же духе! 🚀"
    await message.answer(text, parse_mode="Markdown")


# === Микро веб-сервер для проходимости проверок Render (Web Service) ===
async def handle(request):
    return web.Response(text="Bot with Progress Tracker is running on Render!")


# === Главная функция запуска ===
async def main():
    print("Бот с функцией прогресса запущен!")

    await bot.delete_webhook(drop_pending_updates=True)

    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    await dp.start_polling(bot)


if name == "main":
    asyncio.run(main())