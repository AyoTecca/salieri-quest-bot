import json
import logging
import asyncio
import os

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

class Quest(StatesGroup):
    playing = State()

storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=storage)

try:
    with open("script.json", "r", encoding="utf-8") as f:
        SCRIPT = {step["id"]: step for step in json.load(f)}
except FileNotFoundError:
    logging.critical("Файл script.json не найден! Бот не может запуститься.")
    exit()
except json.JSONDecodeError:
    logging.critical("Ошибка в синтаксисе script.json! Бот не может запуститься.")
    exit()

def get_keyboard(step_id: int):
    """Создает Inline-клавиатуру, используя формат callback_data: "step_id_opt_id" """
    step = SCRIPT[step_id]

    inline_keyboard = []

    for opt in step["options"]:
        opt_id = opt.get("opt_id")

        if opt_id is not None:
            callback_data = f"{step_id}_{opt_id}" 
        else:
            callback_data = "FALLBACK_ERROR"

        inline_keyboard.append([
            types.InlineKeyboardButton(text=opt["text"], callback_data=callback_data)
        ])

    return types.InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


@dp.message(Command("start"))
async def start_game(message: types.Message, state: FSMContext): 
    await state.clear() 

    await state.set_state(Quest.playing) 

    await state.update_data(step_id=0) 

    step = SCRIPT[0]
    await message.answer(step["text"], reply_markup=get_keyboard(0))

@dp.message(F.text, ~F.state) 
async def not_in_game(message: types.Message):
    await message.answer("Напиши /start чтобы начать квест.")

@dp.callback_query(Quest.playing)
async def handle_callback(callback: types.CallbackQuery, state: FSMContext):

    user_data = await state.get_data()
    current_step_id = user_data.get("step_id")

    chosen_option = None
    next_id = None

    try:
        current_id_from_callback, chosen_opt_id = map(int, callback.data.split('_'))

        if current_step_id is None or current_step_id != current_id_from_callback:
            await callback.answer("Произошла ошибка квеста... 😢\nНачните заново /start", show_alert=True)
            await state.clear() 
            return

        step = SCRIPT.get(current_step_id)
        if not step:
            await callback.answer("Произошла ошибка квеста... 😢\nНачните заново /start", show_alert=True)
            await state.clear() 
            return

        for opt in step["options"]:
            if opt.get("opt_id") == chosen_opt_id:
                chosen_option = opt
                next_id = opt.get("next")
                break

    except ValueError:
        if current_step_id == 8:
            step = SCRIPT.get(current_step_id)
            if step:
                if callback.data == f"{8}_{1}": 
                    chosen_option = step["options"][0]
                    next_id = chosen_option.get("next") 
                elif callback.data == f"{8}_{2}": 
                    chosen_option = step["options"][1]
                    next_id = chosen_option.get("next") 

        if not chosen_option:
            await callback.answer("Ошибка! Пожалуйста, используйте кнопки последнего сообщения или начните заново /start.", show_alert=True)
            await state.clear()
            return


    if not chosen_option:
        await callback.answer("Ошибка! Не удалось найти выбранную опцию. Пожалуйста, начните заново /start.", show_alert=True)
        await state.clear()
        return

    await callback.message.edit_reply_markup(reply_markup=None) 

    await callback.message.answer(chosen_option["text"])

    await callback.message.answer(chosen_option["reply"])
    await asyncio.sleep(0.5) 

    if next_id is not None:
        if next_id not in SCRIPT:
            await callback.message.answer("Ошибка в сценарии... 😢\nДавай начнём заново.")
            await state.clear()
            return

        if next_id == 8:
            await state.update_data(step_id=next_id)
            next_step = SCRIPT[next_id]
            await callback.message.answer(next_step["text"])

            await callback.message.answer("Что дальше?", reply_markup=get_keyboard(next_id))

        elif next_id == 0:
            await state.clear()
            await state.set_state(Quest.playing) 
            await state.update_data(step_id=0) 
            next_step = SCRIPT[0]
            await callback.message.answer(next_step["text"], reply_markup=get_keyboard(0))

        else:
            await state.update_data(step_id=next_id)
            next_step = SCRIPT[next_id]
            await callback.message.answer(next_step["text"], reply_markup=get_keyboard(next_id))
    else:
        await callback.message.answer("Конец сценария 👋")
        await state.clear() 

    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())