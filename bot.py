import json
import logging
import asyncio
import os

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile
from dotenv import load_dotenv

CERTIFICATE_FILE = "certificate.png" 

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
    step = SCRIPT[step_id]
    
    inline_keyboard = []
    
    for opt in step["options"]:
        if "next" in opt:
            callback_data = str(opt["next"])
        else:
            callback_data = "END_QUEST" 

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
    step_id = user_data.get("step_id") 
    next_id_str = callback.data        
    
    if step_id is None or step_id not in SCRIPT:
        await callback.answer("Произошла ошибка квеста... 😢\nНачните заново /start", show_alert=True)
        await state.clear() 
        return

    step = SCRIPT[step_id]
    chosen_option = None

    for opt in step["options"]:
        if "next" in opt and str(opt["next"]) == next_id_str:
            chosen_option = opt
            break
        elif "next" not in opt and next_id_str == "END_QUEST":
            chosen_option = opt
            break
            
    if not chosen_option:
        await callback.answer("Ошибка! Пожалуйста, используйте кнопки последнего сообщения.", show_alert=True)
        return

    await callback.message.edit_reply_markup(reply_markup=None) 
    
    await callback.message.answer(chosen_option["reply"])
    await asyncio.sleep(0.5) 

    if next_id_str != "END_QUEST":
        next_id = int(next_id_str)

        if next_id not in SCRIPT:
            await callback.message.answer("Ошибка в сценарии... 😢\nДавай начнём заново.")
            await state.clear()
            return
            
        if next_id == 8:
            next_step = SCRIPT[next_id]
            await callback.message.answer(next_step["text"])
            
            if os.path.exists(CERTIFICATE_FILE):
                certificate = FSInputFile(CERTIFICATE_FILE)
                await callback.message.answer_photo(
                    photo=certificate, 
                    caption="Твой виртуальный «Сертификат исследователя Пушкина»! 🎉"
                )

            await state.update_data(step_id=next_id)
            await callback.message.answer("Что дальше?", reply_markup=get_keyboard(next_id))
        
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