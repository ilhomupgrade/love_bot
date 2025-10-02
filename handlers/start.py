"""
Обработчики команды /start и присоединения к сессии
"""

from aiogram import Router, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import async_session_maker
from db.models import Session as DBSession, Answer
from services.utils import generate_join_link

router = Router()


@router.message(Command("start"))
async def start_cmd(message: types.Message):
    """Приветствие с красивым онбордингом"""
    # Проверяем, есть ли deep link параметр
    args = message.text.split()[1] if len(message.text.split()) > 1 else None

    if args and args.startswith("join_"):
        # Это присоединение к сессии
        await join_session_deep_link(message, args)
        return

    if args and args.startswith("quick_"):
        # Это быстрая проверка с уже существующим пользователем
        await quick_check_deep_link(message, args)
        return

    # Обычный старт - показываем приветствие
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Пройти тест", callback_data="create_session")]
    ])

    await message.answer(
        "❤️ **Привет! Я — LoveBot**\n\n"
        "Хочешь узнать, насколько вы совместимы?\n\n"
        "Пройди быстрый тест вместе с партнёром.\n"
        "⏱ Это займёт всего 2 минуты!",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "create_session")
async def create_session_callback(callback: types.CallbackQuery):
    """Создание сессии после нажатия кнопки"""
    async with async_session_maker() as session:
        # Создаём новую сессию
        new_session = DBSession(
            partner1_user_id=callback.from_user.id,
            status="pending"
        )
        session.add(new_session)
        await session.commit()
        await session.refresh(new_session)

        # Генерируем ссылку для второго партнёра
        bot_username = (await callback.bot.me()).username
        share_link = f"https://t.me/{bot_username}?start=join_{new_session.id}_partner2"

        # Кнопки для отправки ссылки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Отправить партнёру",
                                url=f"https://t.me/share/url?url={share_link}&text=Пройди тест на совместимость со мной! ❤️")],
            [InlineKeyboardButton(text="💬 Отправить в Telegram",
                                switch_inline_query=f"Пройди тест на совместимость со мной! {share_link}")]
        ])

        await callback.message.edit_text(
            "🔗 **Вот твоя личная ссылка!**\n\n"
            "Отправь её партнёру, чтобы пройти тест вместе!\n\n"
            "💡 Результаты откроются только после того, как ответите оба 😉\n\n"
            "📋 **Ссылка для копирования:**\n"
            f"`{share_link}`\n\n"
            "👆 Нажми на ссылку выше, чтобы скопировать",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    await callback.answer()


async def join_session_deep_link(message: types.Message, args: str):
    """Присоединение через deep link"""
    try:
        # Парсим: join_123_partner2
        parts = args.split("_")
        session_id = int(parts[1])
        role = parts[2]

        async with async_session_maker() as session:
            # Находим сессию
            result = await session.execute(
                select(DBSession).where(DBSession.id == session_id)
            )
            db_session = result.scalar_one_or_none()

            if not db_session:
                await message.answer("❌ Сессия не найдена. Проверьте правильность ссылки.")
                return

            if db_session.status != "pending":
                await message.answer("❌ Эта сессия уже началась или завершена.")
                return

            # Проверяем, что второй партнёр ещё не присоединился (защита от race condition)
            if db_session.partner2_user_id is not None:
                await message.answer("❌ К этой сессии уже присоединился другой пользователь.")
                return

            # Обновляем сессию
            if role == "partner2":
                db_session.partner2_user_id = message.from_user.id
                db_session.status = "in_progress"
                await session.commit()

                # Кнопка для старта теста
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎯 Начать тест", callback_data="start_test")]
                ])

                # Уведомляем второго партнёра
                await message.answer(
                    "✅ **Ты успешно присоединился к сессии!**\n\n"
                    "Теперь вы оба можете пройти тест.\n"
                    "Нажми кнопку ниже, чтобы начать 👇",
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )

                # Уведомляем первого партнёра
                if db_session.partner1_user_id:
                    try:
                        keyboard_p1 = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🎯 Начать тест", callback_data="start_test")]
                        ])
                        await message.bot.send_message(
                            db_session.partner1_user_id,
                            "✅ **Твой партнёр присоединился!**\n\n"
                            "Теперь вы оба можете пройти тест.\n"
                            "Нажми кнопку ниже, чтобы начать 👇",
                            parse_mode="Markdown",
                            reply_markup=keyboard_p1
                        )
                    except Exception:
                        pass

            else:
                await message.answer("❌ Неверная роль в ссылке.")

    except (IndexError, ValueError):
        await message.answer("❌ Неверный формат ссылки для присоединения.")


@router.message(Command("quick_check"))
async def quick_check_command(message: types.Message):
    """Быстрая проверка совместимости для тех, кто уже проходил тест"""
    async with async_session_maker() as session:
        # Проверяем, есть ли у пользователя хотя бы один пройденный тест
        result = await session.execute(
            select(Answer).where(Answer.user_id == message.from_user.id)
            .order_by(Answer.completed_at.desc())
            .limit(1)
        )
        last_answer = result.scalar_one_or_none()

        if not last_answer:
            await message.answer(
                "❌ **У тебя нет пройденных тестов**\n\n"
                "Сначала пройди тест командой /start, а потом сможешь быстро проверять совместимость с новыми людьми!",
                parse_mode="Markdown"
            )
            return

        # Создаём новую сессию для быстрой проверки
        new_session = DBSession(
            partner1_user_id=message.from_user.id,
            status="quick_check"  # специальный статус
        )
        session.add(new_session)
        await session.commit()
        await session.refresh(new_session)

        # Генерируем ссылку для нового партнёра
        bot_username = (await message.bot.me()).username
        share_link = f"https://t.me/{bot_username}?start=quick_{new_session.id}_{message.from_user.id}"

        # Кнопки для отправки ссылки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Отправить партнёру",
                                url=f"https://t.me/share/url?url={share_link}&text=Проверим нашу совместимость! ❤️")],
            [InlineKeyboardButton(text="💬 Отправить в Telegram",
                                switch_inline_query=f"Проверим нашу совместимость! {share_link}")]
        ])

        await message.answer(
            "⚡️ **Быстрая проверка совместимости**\n\n"
            "Отправь эту ссылку человеку, с которым хочешь проверить совместимость!\n\n"
            "Он пройдёт тест, а система автоматически сравнит его ответы с твоими последними результатами.\n\n"
            "💡 **Тебе больше не нужно проходить тест заново!**\n\n"
            "📋 **Ссылка для копирования:**\n"
            f"`{share_link}`\n\n"
            "👆 Нажми на ссылку выше, чтобы скопировать",
            parse_mode="Markdown",
            reply_markup=keyboard
        )


async def quick_check_deep_link(message: types.Message, args: str):
    """Обработка быстрой проверки через deep link"""
    try:
        # Парсим: quick_123_456 (session_id_original_user_id)
        parts = args.split("_")
        session_id = int(parts[1])
        original_user_id = int(parts[2])

        # Проверяем, что это не тот же пользователь
        if message.from_user.id == original_user_id:
            await message.answer(
                "❌ **Ты не можешь проверить совместимость сам с собой!** 😄\n\n"
                "Отправь эту ссылку другому человеку.",
                parse_mode="Markdown"
            )
            return

        async with async_session_maker() as session:
            # Проверяем, есть ли у оригинального пользователя ответы
            result = await session.execute(
                select(Answer).where(Answer.user_id == original_user_id)
                .order_by(Answer.completed_at.desc())
                .limit(1)
            )
            original_answer = result.scalar_one_or_none()

            if not original_answer:
                await message.answer(
                    "❌ У создателя ссылки нет пройденных тестов.\n"
                    "Попросите его сначала пройти тест!",
                    parse_mode="Markdown"
                )
                return

            # Находим сессию
            result = await session.execute(
                select(DBSession).where(DBSession.id == session_id)
            )
            db_session = result.scalar_one_or_none()

            if not db_session:
                await message.answer("❌ Сессия не найдена. Проверьте правильность ссылки.")
                return

            # Обновляем сессию - добавляем второго партнёра
            db_session.partner2_user_id = message.from_user.id
            db_session.status = "in_progress"
            await session.commit()

            # Кнопка для старта теста
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎯 Пройти тест", callback_data="start_test")]
            ])

            # Получаем имя отправителя
            try:
                original_user = await message.bot.get_chat(original_user_id)
                original_name = original_user.first_name or "Пользователь"
            except:
                original_name = "Пользователь"

            await message.answer(
                f"⚡️ **Быстрая проверка совместимости с {original_name}**\n\n"
                f"Тебе нужно пройти короткий тест из 5 вопросов.\n"
                f"После этого ты сразу получишь результаты совместимости!\n\n"
                f"💡 {original_name} уже проходил этот тест, поэтому ему не нужно проходить заново.\n\n"
                f"Нажми кнопку ниже, чтобы начать 👇",
                parse_mode="Markdown",
                reply_markup=keyboard
            )

    except (IndexError, ValueError):
        await message.answer("❌ Неверный формат ссылки для быстрой проверки.")
