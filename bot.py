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
    step = SCRIPT[step_id]
    
    keyboard_buttons = []
    
    for opt in step["options"]:
        keyboard_buttons.append([types.KeyboardButton(text=opt["text"])])
        
    return types.ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True,
        one_time_keyboard=True 
    )


@dp.message(Command("start"))
async def start_game(message: types.Message, state: FSMContext): 
    await state.clear() 
    await state.set_state(Quest.playing) 
    await state.update_data(step_id=0) 
    
    step = SCRIPT[0]
    await message.answer(step["text"], reply_markup=get_keyboard(0))

@dp.message(F.text, Quest.playing) 
async def handle_message(message: types.Message, state: FSMContext):
    
    user_data = await state.get_data()
    current_step_id = user_data.get("step_id")
    
    chosen_option = None
    next_id = None
    
    step = SCRIPT.get(current_step_id)
    if not step:
        await message.answer("Произошла ошибка квеста... 😢\nНачните заново /start", reply_markup=types.ReplyKeyboardRemove())
        await state.clear() 
        return

    for opt in step["options"]:
        if opt["text"] == message.text:
            chosen_option = opt
            next_id = opt.get("next")
            break

    if not chosen_option:
        await message.answer("Пожалуйста, выберите одну из предложенных кнопок.", reply_markup=get_keyboard(current_step_id))
        return

    
    await message.answer(chosen_option["reply"])
    await asyncio.sleep(0.5) 

    if next_id is not None:
        if next_id not in SCRIPT:
            await message.answer("Ошибка в сценарии... 😢\nДавай начнём заново.", reply_markup=types.ReplyKeyboardRemove())
            await state.clear()
            return
            
        if next_id == 8:
            await state.update_data(step_id=next_id)
            next_step = SCRIPT[next_id]
            await message.answer(next_step["text"], reply_markup=get_keyboard(next_id))
        
        elif next_id == 0:
            await state.clear()
            await state.set_state(Quest.playing) 
            await state.update_data(step_id=0) 
            next_step = SCRIPT[0]
            await message.answer(next_step["text"], reply_markup=get_keyboard(0))
        
        else:
            await state.update_data(step_id=next_id)
            next_step = SCRIPT[next_id]
            await message.answer(next_step["text"], reply_markup=get_keyboard(next_id))
    else:
        await message.answer("Конец сценария 👋", reply_markup=types.ReplyKeyboardRemove())
        await state.clear() 


@dp.message(F.text, ~F.state) 
async def not_in_game_text(message: types.Message):
    await message.answer("Напиши /start чтобы начать квест.", reply_markup=types.ReplyKeyboardRemove())


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())