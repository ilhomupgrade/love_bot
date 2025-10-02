"""
Обработчики просмотра результатов и премиум-функций
"""

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import os

from db.database import async_session_maker
from db.models import Session as DBSession, Result
from services.pdf_generator import generate_pdf_report
from config import ADMIN_IDS

router = Router()


@router.message(Command("results"))
async def show_results(message: types.Message):
    """Показать результаты последней сессии"""
    async with async_session_maker() as session:
        # Находим завершённую сессию пользователя (самую свежую)
        result = await session.execute(
            select(DBSession).where(
                and_(
                    (DBSession.partner1_user_id == message.from_user.id) |
                    (DBSession.partner2_user_id == message.from_user.id),
                    DBSession.status == "completed"
                )
            ).order_by(DBSession.created_at.desc()).limit(1)
        )
        db_session = result.scalar_one_or_none()

        if not db_session:
            await message.answer(
                "❌ У тебя нет завершённых сессий.\n\n"
                "Пройди тест командой /test"
            )
            return

        # Получаем результаты
        result = await session.execute(
            select(Result).where(Result.session_id == db_session.id)
        )
        test_result = result.scalar_one_or_none()

        if not test_result:
            await message.answer("❌ Результаты не найдены.")
            return

        # Показываем бесплатную версию
        from config import FREE_REPORT_LIMIT
        free_report = test_result.report[:FREE_REPORT_LIMIT]
        if len(test_result.report) > FREE_REPORT_LIMIT:
            free_report += "\n\n...\n\n💎 **Полный отчёт доступен в платной версии**"

        await message.answer(
            f"📊 **Твои результаты**\n\n"
            f"💕 **Индекс совместимости: {test_result.compatibility_score}%**\n\n"
            f"{free_report}\n\n"
            f"Для получения полного отчёта используйте /premium",
            parse_mode="Markdown"
        )


@router.callback_query(F.data.startswith("premium_"))
async def show_premium_offer(callback: types.CallbackQuery):
    """Показать предложение премиум-версии"""
    session_id = int(callback.data.split("_")[1])

    # Кнопки для покупки
    keyboard_buttons = [
        [InlineKeyboardButton(text="💳 Купить отчёт за 299₽", callback_data=f"buy_{session_id}")],
    ]

    # Добавляем тестовую кнопку для администраторов
    if callback.from_user.id in ADMIN_IDS:
        keyboard_buttons.append(
            [InlineKeyboardButton(text="🧪 ТЕСТ: Получить PDF бесплатно", callback_data=f"test_pdf_{session_id}")]
        )

    keyboard_buttons.append(
        [InlineKeyboardButton(text="❌ Остаться с бесплатным", callback_data="cancel_premium")]
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await callback.message.edit_text(
        "💎 **Полный отчёт о совместимости**\n\n"
        "В полном отчёте вы узнаете:\n\n"
        "💘 Подробный анализ ваших языков любви\n"
        "🔥 3 главные зоны конфликта\n"
        "🛠 Практические советы, как справляться\n"
        "🎨 Красивую картинку для соцсетей\n"
        "📊 Графики совместимости\n\n"
        "**Цена: всего 299 ₽**",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_"))
async def process_payment(callback: types.CallbackQuery):
    """Обработка покупки (здесь должна быть интеграция с платёжной системой)"""
    session_id = int(callback.data.split("_")[1])

    async with async_session_maker() as session:
        # Получаем результаты и информацию о сессии
        result = await session.execute(
            select(Result).where(Result.session_id == session_id).limit(1)
        )
        test_result = result.scalar_one_or_none()

        if not test_result:
            await callback.answer("❌ Результаты не найдены.", show_alert=True)
            return

        # Получаем информацию о партнёрах
        db_session_result = await session.execute(
            select(DBSession).where(DBSession.id == session_id).limit(1)
        )
        db_session = db_session_result.scalar_one_or_none()

        # В реальности здесь должна быть оплата через Telegram Payments или YooKassa
        # Пока показываем полный отчёт сразу

        # Уведомление о генерации PDF
        await callback.message.edit_text(
            "⏳ Генерирую красивый PDF отчёт...",
            parse_mode="Markdown"
        )

        # Генерируем PDF
        try:
            # Получаем имена пользователей (если есть)
            partner1_name = "Partner 1"
            partner2_name = "Partner 2"

            # Можно попытаться получить имена из Telegram (используем только ASCII)
            try:
                user1_info = await callback.bot.get_chat(db_session.partner1_user_id)
                if user1_info.first_name:
                    partner1_name = user1_info.first_name.encode('ascii', 'ignore').decode('ascii') or "Partner 1"
            except:
                pass

            try:
                user2_info = await callback.bot.get_chat(db_session.partner2_user_id)
                if user2_info.first_name:
                    partner2_name = user2_info.first_name.encode('ascii', 'ignore').decode('ascii') or "Partner 2"
            except:
                pass

            pdf_path = generate_pdf_report(
                compatibility_score=test_result.compatibility_score,
                report=test_result.report,
                partner1_name=partner1_name,
                partner2_name=partner2_name
            )

            # Отправляем PDF
            pdf_file = FSInputFile(pdf_path)

            # Кнопки после покупки
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎁 Подписка LoveBot+ за 399₽/мес", callback_data="subscription")],
                [InlineKeyboardButton(text="📤 Поделиться результатом",
                                    switch_inline_query=f"Мы прошли тест на совместимость! Наш результат: {test_result.compatibility_score}%")]
            ])

            await callback.message.answer_document(
                document=pdf_file,
                caption=(
                    f"💎 **ПРЕМИУМ ОТЧЁТ**\n\n"
                    f"💕 **Индекс совместимости: {test_result.compatibility_score}%**\n\n"
                    f"✨ **Спасибо за покупку!**\n\n"
                    f"📄 Ваш красивый PDF отчёт готов!\n\n"
                    f"Хотите получать еженедельные мини-тесты и советы для вашей пары?\n"
                    f"Оформите подписку LoveBot+ 🚀"
                ),
                parse_mode="Markdown",
                reply_markup=keyboard
            )

            # Удаляем сообщение о генерации
            await callback.message.delete()

            # Удаляем временный PDF файл
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

        except Exception as e:
            # Отправляем короткое сообщение об ошибке и текстовый отчёт отдельно
            await callback.message.edit_text(
                f"❌ Ошибка при генерации PDF\n\n"
                f"Отправляю текстовый отчёт...",
                parse_mode="Markdown"
            )
            # Отчёт может быть длинным, разбиваем его
            report_parts = [test_result.report[i:i+4000] for i in range(0, len(test_result.report), 4000)]
            for part in report_parts:
                await callback.message.answer(part, parse_mode="Markdown")

    await callback.answer("✅ Оплата прошла успешно!", show_alert=True)


@router.callback_query(F.data.startswith("test_pdf_"))
async def test_pdf_generation(callback: types.CallbackQuery):
    """Тестовая генерация PDF для администраторов"""
    # Проверка прав доступа
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return

    session_id = int(callback.data.split("_")[2])

    async with async_session_maker() as session:
        # Получаем результаты и информацию о сессии
        result = await session.execute(
            select(Result).where(Result.session_id == session_id).limit(1)
        )
        test_result = result.scalar_one_or_none()

        if not test_result:
            await callback.answer("❌ Результаты не найдены.", show_alert=True)
            return

        # Получаем информацию о партнёрах
        db_session_result = await session.execute(
            select(DBSession).where(DBSession.id == session_id).limit(1)
        )
        db_session = db_session_result.scalar_one_or_none()

        # Уведомление о генерации PDF
        await callback.message.edit_text(
            "🧪 **ТЕСТОВЫЙ РЕЖИМ**\n\n"
            "⏳ Генерирую PDF отчёт...",
            parse_mode="Markdown"
        )

        # Генерируем PDF
        try:
            # Получаем имена пользователей (используем только ASCII)
            partner1_name = "Partner 1"
            partner2_name = "Partner 2"

            try:
                user1_info = await callback.bot.get_chat(db_session.partner1_user_id)
                if user1_info.first_name:
                    partner1_name = user1_info.first_name.encode('ascii', 'ignore').decode('ascii') or "Partner 1"
            except:
                pass

            try:
                user2_info = await callback.bot.get_chat(db_session.partner2_user_id)
                if user2_info.first_name:
                    partner2_name = user2_info.first_name.encode('ascii', 'ignore').decode('ascii') or "Partner 2"
            except:
                pass

            pdf_path = generate_pdf_report(
                compatibility_score=test_result.compatibility_score,
                report=test_result.report,
                partner1_name=partner1_name,
                partner2_name=partner2_name
            )

            # Отправляем PDF
            pdf_file = FSInputFile(pdf_path)

            await callback.message.answer_document(
                document=pdf_file,
                caption=(
                    f"🧪 **ТЕСТОВЫЙ PDF ОТЧЁТ**\n\n"
                    f"💕 **Индекс совместимости: {test_result.compatibility_score}%**\n\n"
                    f"📄 Это тестовая версия для проверки генерации PDF.\n"
                    f"Доступна только для администраторов."
                ),
                parse_mode="Markdown"
            )

            # Удаляем сообщение о генерации
            await callback.message.delete()

            # Удаляем временный PDF файл
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

        except Exception as e:
            await callback.message.edit_text(
                f"❌ Ошибка при генерации PDF\n\n"
                f"Попробуйте снова или обратитесь в поддержку.",
                parse_mode="Markdown"
            )

    await callback.answer("🧪 Тестовый PDF сгенерирован!", show_alert=True)


@router.callback_query(F.data == "cancel_premium")
async def cancel_premium(callback: types.CallbackQuery):
    """Отказ от премиум-версии"""
    await callback.message.edit_text(
        "✅ Хорошо! Ты всегда можешь вернуться к полному отчёту позже.\n\n"
        "Используй команду /results чтобы снова посмотреть результаты.",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "subscription")
async def show_subscription(callback: types.CallbackQuery):
    """Показать информацию о подписке"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оформить подписку", callback_data="buy_subscription")],
        [InlineKeyboardButton(text="❌ Может позже", callback_data="cancel_subscription")]
    ])

    await callback.message.edit_text(
        "🚀 **LoveBot+ Подписка**\n\n"
        "Что входит в подписку:\n\n"
        "📅 Еженедельные мини-тесты\n"
        "💡 Персональные советы психолога\n"
        "📊 Трекинг динамики отношений\n"
        "🎯 Челленджи для пар\n"
        "💬 Приоритетная поддержка\n\n"
        "**Цена: 399₽/месяц**",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "buy_subscription")
async def buy_subscription(callback: types.CallbackQuery):
    """Покупка подписки"""
    # В реальности здесь должна быть интеграция с платёжной системой
    await callback.message.edit_text(
        "✅ **Подписка активирована!**\n\n"
        "Спасибо! Теперь ты получаешь полный доступ к LoveBot+\n\n"
        "Первый еженедельный тест придёт через 7 дней 📅",
        parse_mode="Markdown"
    )
    await callback.answer("✅ Подписка оформлена!", show_alert=True)


@router.callback_query(F.data == "cancel_subscription")
async def cancel_subscription(callback: types.CallbackQuery):
    """Отказ от подписки"""
    await callback.message.edit_text(
        "Хорошо! Если передумаешь, всегда можешь вернуться 😊",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(Command("help"))
async def help_command(message: types.Message):
    """Справка по командам бота"""
    help_text = """
❤️ **LoveBot - Бот для проверки совместимости**

**Доступные команды:**

/start - Создать новую сессию
/test - Пройти тест на совместимость
/quick_check - ⚡️ Быстрая проверка (для тех, кто уже проходил тест)
/results - Показать результаты последнего теста
/premium - Получить полный отчёт (премиум)
/help - Эта справка

**Как это работает:**

📝 **Обычный тест:**
1. Создай сессию командой /start
2. Отправь партнёру ссылку для присоединения
3. Оба пройдите тест командой /test
4. Получите результаты автоматически

⚡️ **Быстрая проверка:**
1. Если ты уже проходил тест - используй /quick_check
2. Отправь ссылку новому человеку
3. Он пройдёт тест, а твои старые ответы будут использованы автоматически
4. Получите результаты сразу после его теста!

**Поддержка:** @your_support_bot
"""
    await message.answer(help_text, parse_mode="Markdown")
