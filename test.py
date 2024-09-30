import os
from random import choice, uniform, randint
import asyncio
import datetime

from aiogram import F, Router, types, Bot
from aiogram.filters.command import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import CHANNEL_ID, REF_URL
from keyboards.client import ClientKeyboard
from other.filters import ChatJoinFilter, RegisteredFilter
from database.db import DataBase

router = Router()


class RegisterState(StatesGroup):
    input_id = State()


class GetSignalStates(StatesGroup):
    chosing_mines = State()


# Получаем язык пользователя из базы данных
async def get_user_language(user_id):
    user = await DataBase.get_user(user_id)
    if user and user['language']:
        return user['language']
    return 'ru'  # По умолчанию русский


# Обновляем язык пользователя в базе данных
async def set_user_language(user_id, language):
    await DataBase.update_language(user_id, language)


# Хендлер для смены языка
@router.callback_query(F.data == "change_language")
async def change_language_handler(callback: types.CallbackQuery):
    await callback.message.edit_text("Выберите язык / Choose a language:",
                                     reply_markup=await ClientKeyboard.language_keyboard())


@router.callback_query(F.data.in_(["lang_ru", "lang_en"]))
async def set_language_handler(callback: types.CallbackQuery):
    if callback.data == "lang_ru":
        await set_user_language(callback.from_user.id, "ru")
        await callback.message.answer("Язык изменен на русский 🇷🇺", reply_markup=await ClientKeyboard.start_keyboard(language="ru"))
    elif callback.data == "lang_en":
        await set_user_language(callback.from_user.id, "en")
        await callback.message.answer("Language changed to English 🇬🇧", reply_markup=await ClientKeyboard.start_keyboard(language="en"))

    await callback.message.delete()


# Обработчик команды /start с учетом языка
@router.message(CommandStart())
async def start_command(message: types.Message, bot: Bot):
    await DataBase.register(message.from_user.id, verifed="0")
    language = await get_user_language(message.from_user.id)

    texts = {
        "ru": f"""
Добро пожаловать, <b>{message.from_user.first_name}!</b>

Для использования бота - <b>подпишись</b> на наш канал🤝""",
        "en": f"""
Welcome, <b>{message.from_user.first_name}!</b>

To use the bot - <b>subscribe</b> to our channel🤝"""
    }

    await message.answer(texts[language], reply_markup=await ClientKeyboard.start_keyboard(language=language), parse_mode="HTML")


# Обработчик для проверки и возврата в меню
@router.callback_query(F.data.in_(["check", "back"]), ChatJoinFilter())
async def menu_output(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
    except:
        pass

    language = await get_user_language(callback.from_user.id)

    texts = {
        "ru": """
Добро пожаловать в 🔸<b>TRAFF MINES</b>🔸!

💣Mines - это гемблинг игра в букмекерской конторе 1win, которая основывается на классическом “Сапёре”.
Ваша цель - открывать безопасные ячейки и не попадаться в ловушки.

<code>Наш бот основан на нейросети от OpenAI. ChatGPT 4.0
Он может предугадать расположение звёзд с вероятностью 90%.</code>

❗️ ВНИМАНИЕ ❗️
Бот работает корректно, только с новыми аккаунтами (инструкция по регистрации есть ниже по кнопке)
❗️ ДЛЯ игры без риска ❗️
Нужен новый, чистый аккаунт, в котором при первом
депозите нужно ввести промокод TRAFF500 который даст +500% к депозиту (инструкция по кнопке ниже)""",
        "en": """
Welcome to 🔸<b>TRAFF MINES</b>🔸!

💣Mines is a gambling game in the 1win bookmaker, which is based on the classic “Minesweeper”.
Your goal is to open safe cells and avoid traps.

<code>Our bot is based on the OpenAI neural network. ChatGPT 4.0
It can predict the location of stars with 90% accuracy.</code>

❗️ WARNING ❗️
The bot works correctly only with new accounts (registration instructions are below).
❗️ FOR risk-free play ❗️
You need a new, clean account, where upon your first deposit you need to enter the promo code TRAFF500, which will give +500% to the deposit (instruction below)."""
    }

    photo = types.FSInputFile("traffsignal2.png")
    await callback.message.answer_photo(
        photo=photo,
        caption=texts[language],
        parse_mode="HTML",
        reply_markup=await ClientKeyboard.menu_keyboard(language=language)
    )
    await callback.answer()


# Обработчик регистрации
@router.callback_query(F.data == "register")
async def register_handler(callback: types.CallbackQuery, state: FSMContext):
    language = await get_user_language(callback.from_user.id)

    texts = {
        "ru": f"""
🔷 1. Для начала зарегистрируйтесь по ссылке на сайте с ОБЯЗАТЕЛЬНЫМ использованием промокода TRAFF500 <a href="{REF_URL}">1WIN(CLICK)</a>
🔷 2. После успешной регистрации скопируйте ваш айди на сайте (Вкладка 'пополнение' и в правом верхнем углу будет ваш ID).
🔷 3. И отправьте его боту в ответ на это сообщение!""",
        "en": f"""
🔷 1. First, register using the link on the site with the REQUIRED use of the promo code TRAFF500 <a href="{REF_URL}">1WIN(CLICK)</a>
🔷 2. After successful registration, copy your ID on the website (Tab 'Deposit' and your ID will be in the upper right corner).
🔷 3. And send it to the bot in response to this message!"""
    }

    try:
        await callback.message.delete()
    except:
        pass

    photo = types.FSInputFile("reg.png")  # Загрузить изображение

    await callback.message.answer_photo(
        photo=photo,
        caption=texts[language],
        parse_mode="HTML",
        reply_markup=await ClientKeyboard.register_keyboard(language=language)
    )
    await state.set_state(RegisterState.input_id)


# Обработчик получения ID для регистрации
@router.message(RegisterState.input_id)
async def register_handler_final(message: types.Message, state: FSMContext):
    try:
        number = int(message.text)

        if len(message.text) >= 8:
            await DataBase.update_verifed(message.from_user.id)
            language = await get_user_language(message.from_user.id)
            texts = {
                "ru": "Вы успешно зарегестрировались",
                "en": "You have successfully registered"
            }
            await message.answer(texts[language], reply_markup=await ClientKeyboard.on_register_keyboard(language=language))
            await state.clear()
        else:
            await message.answer("Неверный ID")
            return

    except Exception as e:
        await message.answer("Неверный ID")
        return


# Обработчик для инструкции
@router.callback_query(F.data == "instruction")
async def instruction_handler(callback: types.CallbackQuery):
    language = await get_user_language(callback.from_user.id)

    texts = {
        "ru": f"""
Бот основан и обучен на кластере нейросети 🖥 <strong>[TRAFF MINES]</strong>.
Для тренировки бота было сыграно 🎰10.000+ игр.

В данный момент пользователи бота успешно делают в день 20-30% от своего 💸 капитала!
<code>На текущий момент бот по сей день проходит проверки и  исправления! Точность бота составляет 92%!</code>
Для получения максимального профита следуйте следующей инструкции:

🟢 1. Пройти регистрацию в букмекерской конторе <a href="{REF_URL}">1WIN</a>
Если не открывается - заходим с включенным VPN (Швеция). В Play Market/App Store полно бесплатных сервисов, например: Vpnify, Planet VPN, Hotspot VPN и так далее!
<code>Без регистрации по промокоду TRAFF500 доступ к сигналам не будет открыт!</code>
🟢 2. Пополнить баланс своего аккаунта.
🟢 3. Перейти в раздел 1win games и выбрать игру 💣'MINES'.
🟢 4. Выставить кол-во ловушек в размере трёх. Это важно!
🟢 5. Запросить сигнал в боте и ставить по сигналам из бота.
🟢 6. При неудачном сигнале советуем удвоить ставку и воспользоваться сигналом повторно.""",
        "en": f"""
The bot is based and trained on the neural network cluster 🖥 <strong>[TRAFF MINES]</strong>.
For bot training, 🎰10,000+ games were played.

Currently, bot users successfully earn 20-30% of their 💸 capital per day!
<code>At present, the bot is still undergoing tests and fixes! The bot's accuracy is 92%!</code>
To achieve maximum profit, follow these instructions:

🟢 1. Register in the bookmaker's office <a href="{REF_URL}">1WIN</a>.
If it doesn’t open - use VPN (set to Sweden). In Play Market/App Store, there are plenty of free services like Vpnify, Planet VPN, Hotspot VPN, etc.
<code>Access to signals will not be opened without registration via the TRAFF500 promo code!</code>
🟢 2. Top up your account balance.
🟢 3. Go to the 1win games section and select the 💣'MINES' game.
🟢 4. Set the number of mines to three. This is important!
🟢 5. Request a signal in the bot and follow the signals from the bot.
🟢 6. In case of a failed signal, we recommend doubling the bet and using the signal again."""
    }

    try:
        await callback.message.delete()
    except:
        pass

    await callback.message.answer(texts[language], parse_mode="HTML", reply_markup=await ClientKeyboard.back_to_menu_keyboard(language=language))


# Ожидание ответа от пользователя с его ID для проверки регистрации
@router.message(F.text.regexp(r"\d+"), state=RegisterState.input_id)
async def process_id(message: types.Message, state: FSMContext):
    user_id = message.text
    language = await get_user_language(message.from_user.id)
    try:
        # Логика проверки ID (например, наличие в базе данных)
        if len(user_id) > 7:  # пример проверки
            await message.answer(f"ID {user_id} принято!", reply_markup=await ClientKeyboard.menu_keyboard(language=language))
            await state.clear()
        else:
            await message.answer(f"Некорректный ID. Попробуйте еще раз.", reply_markup=await ClientKeyboard.back_to_menu_keyboard(language=language))
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}. Пожалуйста, повторите ввод.")


# Обработчик кнопки "Сигналы"
@router.callback_query(F.data == "get_signal", RegisteredFilter())
async def get_signal_handler(callback: types.CallbackQuery, state: FSMContext):
    language = await get_user_language(callback.from_user.id)

    texts = {
        "ru": "Выберите количество мин, которое хотите установить (2, 3 или 4 мины)",
        "en": "Choose the number of mines to set (2, 3, or 4 mines)"
    }

    await callback.message.answer(texts[language], reply_markup=await ClientKeyboard.choose_mines_keyboard(language=language))
    await state.set_state(GetSignalStates.chosing_mines)


# Обработчик выбора количества мин
@router.callback_query(GetSignalStates.chosing_mines, F.data.in_(["2_mines", "3_mines", "4_mines"]))
async def choose_mines_handler(callback: types.CallbackQuery, state: FSMContext):
    chosen_mines = callback.data.split("_")[0]
    language = await get_user_language(callback.from_user.id)

    texts = {
        "ru": f"Вы выбрали {chosen_mines} мины. Ожидайте сигнал...",
        "en": f"You selected {chosen_mines} mines. Wait for the signal..."
    }

    await callback.message.answer(texts[language])
    await state.clear()
    # Далее идет логика работы с сигналами, которая зависит от конкретной реализации