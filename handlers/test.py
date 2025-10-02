"""
Обработчики прохождения теста
"""

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import async_session_maker
from db.models import Session as DBSession, Answer
from services.analyzer import analyze
from services.utils import generate_join_link
from config import FREE_REPORT_LIMIT

router = Router()

# Вопросы теста
QUESTIONS = [
    "1️⃣ Что для тебя важнее в отношениях?\n\nA) Проводить много времени вместе ⏰\nB) Получать подарки и сюрпризы 🎁\nC) Слышать слова любви и комплименты 💬\nD) Помощь и поддержка в делах 🤝\nE) Физическая близость и прикосновения 🤗",

    "2️⃣ Как ты чаще всего выражаешь свою любовь?\n\nA) Провожу время с любимым человеком\nB) Дарю подарки\nC) Говорю приятные слова\nD) Помогаю с делами\nE) Обнимаю и целую",

    "3️⃣ Что тебя больше всего обижает в отношениях?\n\nA) Когда партнёр не хочет проводить со мной время\nB) Когда забывают о важных датах\nC) Когда не говорят приятных слов\nD) Когда не помогают, когда нужно\nE) Когда избегают физического контакта",

    "4️⃣ Что тебя делает самым счастливым?\n\nA) Совместные прогулки и путешествия\nB) Неожиданные подарки\nC) Признания в любви\nD) Когда партнёр берёт на себя часть обязанностей\nE) Объятия и поцелуи",

    "5️⃣ Какой идеальный вечер для тебя?\n\nA) Ужин вдвоём в ресторане\nB) Получить букет цветов\nC) Долгий разговор по душам\nD) Когда партнёр приготовил ужин\nE) Обниматься на диване перед фильмом"
]


class TestStates(StatesGroup):
    """Состояния для FSM"""
    waiting_for_answer = State()


@router.callback_query(F.data == "start_test")
async def start_test_callback(callback: types.CallbackQuery, state: FSMContext):
    """Начало теста через callback (кнопка)"""
    await start_test_logic(callback.message, callback.from_user.id, state)
    await callback.answer()


@router.message(Command("test"))
async def start_test_command(message: types.Message, state: FSMContext):
    """Начало теста через команду"""
    await start_test_logic(message, message.from_user.id, state)


async def start_test_logic(message: types.Message, user_id: int, state: FSMContext):
    """Общая логика начала теста"""
    async with async_session_maker() as session:
        # Находим активную сессию пользователя (самую свежую)
        result = await session.execute(
            select(DBSession).where(
                and_(
                    (DBSession.partner1_user_id == user_id) |
                    (DBSession.partner2_user_id == user_id),
                    DBSession.status == "in_progress"
                )
            ).order_by(DBSession.created_at.desc()).limit(1)
        )
        db_session = result.scalar_one_or_none()

        if not db_session:
            await message.answer(
                "❌ У тебя нет активной сессии.\n\n"
                "Создай новую сессию командой /start или присоединись к существующей."
            )
            return

        # Проверяем, не прошёл ли уже пользователь тест
        result = await session.execute(
            select(Answer).where(
                and_(
                    Answer.session_id == db_session.id,
                    Answer.user_id == user_id
                )
            )
        )
        existing_answer = result.scalar_one_or_none()

        if existing_answer:
            await message.answer("✅ Ты уже прошёл этот тест. Ожидай результаты!")
            return

        # Определяем роль пользователя
        role = "partner1" if db_session.partner1_user_id == user_id else "partner2"

        # Сохраняем данные в FSM
        await state.update_data(
            session_id=db_session.id,
            role=role,
            current_question=0,
            answers=[]
        )

        await state.set_state(TestStates.waiting_for_answer)

        # Создаём inline кнопки для ответов
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="A", callback_data="answer_A")],
            [InlineKeyboardButton(text="B", callback_data="answer_B")],
            [InlineKeyboardButton(text="C", callback_data="answer_C")],
            [InlineKeyboardButton(text="D", callback_data="answer_D")],
            [InlineKeyboardButton(text="E", callback_data="answer_E")]
        ])

        await message.answer(
            "🎯 **Тест на совместимость**\n\n"
            "Сейчас я задам тебе 5 вопросов.\n"
            "Выбирай вариант, нажимая на кнопки ниже 👇\n\n" + QUESTIONS[0],
            parse_mode="Markdown",
            reply_markup=keyboard
        )


@router.callback_query(F.data.startswith("answer_"), TestStates.waiting_for_answer)
async def process_answer_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработка ответа через callback"""
    answer = callback.data.split("_")[1]  # Получаем A, B, C, D или E

    data = await state.get_data()
    current_question = data["current_question"]
    answers = data["answers"]

    # Сохраняем ответ
    answers.append(answer)
    current_question += 1

    # Проверяем, есть ли ещё вопросы
    if current_question < len(QUESTIONS):
        await state.update_data(
            current_question=current_question,
            answers=answers
        )

        # Создаём кнопки для следующего вопроса
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="A", callback_data="answer_A")],
            [InlineKeyboardButton(text="B", callback_data="answer_B")],
            [InlineKeyboardButton(text="C", callback_data="answer_C")],
            [InlineKeyboardButton(text="D", callback_data="answer_D")],
            [InlineKeyboardButton(text="E", callback_data="answer_E")]
        ])

        try:
            await callback.message.edit_text(
                QUESTIONS[current_question],
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        except:
            # Если не удалось отредактировать, отправляем новое сообщение
            await callback.message.answer(
                QUESTIONS[current_question],
                parse_mode="Markdown",
                reply_markup=keyboard
            )
    else:
        # Тест завершён - отвечаем на callback и отправляем новое сообщение
        await callback.answer()
        await callback.message.answer("✅ Спасибо! Обрабатываю твои ответы...")
        await finish_test(callback.message, state, answers, user_id=callback.from_user.id)
        return

    await callback.answer()


@router.message(TestStates.waiting_for_answer)
async def process_answer_text(message: types.Message, state: FSMContext):
    """Обработка текстового ответа (на случай если пользователь пишет вручную)"""
    data = await state.get_data()
    current_question = data["current_question"]
    answers = data["answers"]

    # Проверяем формат ответа
    answer = message.text.strip().upper()
    if answer not in ["A", "B", "C", "D", "E"]:
        await message.answer("❌ Пожалуйста, используй кнопки ниже или напиши одну букву: A, B, C, D или E")
        return

    # Сохраняем ответ
    answers.append(answer)
    current_question += 1

    # Проверяем, есть ли ещё вопросы
    if current_question < len(QUESTIONS):
        await state.update_data(
            current_question=current_question,
            answers=answers
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="A", callback_data="answer_A")],
            [InlineKeyboardButton(text="B", callback_data="answer_B")],
            [InlineKeyboardButton(text="C", callback_data="answer_C")],
            [InlineKeyboardButton(text="D", callback_data="answer_D")],
            [InlineKeyboardButton(text="E", callback_data="answer_E")]
        ])

        await message.answer(QUESTIONS[current_question], reply_markup=keyboard)
    else:
        # Тест завершён
        await finish_test(message, state, answers)


async def finish_test(message: types.Message, state: FSMContext, answers: list, user_id: int = None):
    """Завершение теста и сохранение результатов"""
    data = await state.get_data()
    session_id = data["session_id"]
    role = data["role"]

    # Используем переданный user_id или берём из message
    if user_id is None:
        user_id = message.from_user.id

    async with async_session_maker() as session:
        # Получаем информацию о сессии
        session_result = await session.execute(
            select(DBSession).where(DBSession.id == session_id)
        )
        db_session = session_result.scalar_one_or_none()

        # Проверяем, это быстрая проверка или обычный тест
        is_quick_check = db_session.status in ["quick_check", "in_progress"] and db_session.partner1_user_id != user_id

        if is_quick_check:
            # Это быстрая проверка - используем старые ответы первого партнёра
            # Получаем последние ответы первого партнёра
            result = await session.execute(
                select(Answer).where(Answer.user_id == db_session.partner1_user_id)
                .order_by(Answer.completed_at.desc())
                .limit(1)
            )
            partner1_old_answer = result.scalar_one_or_none()

            if partner1_old_answer:
                # Создаём виртуальный Answer для текущей сессии с ответами первого партнёра
                answer_partner1 = Answer(
                    session_id=session_id,
                    user_id=db_session.partner1_user_id,
                    user_role="partner1",
                    answers=partner1_old_answer.answers
                )
                session.add(answer_partner1)

                # Сохраняем ответы второго партнёра (текущего пользователя)
                new_answer = Answer(
                    session_id=session_id,
                    user_id=user_id,
                    user_role="partner2",
                    answers=answers
                )
                session.add(new_answer)
                await session.commit()

                await message.answer(
                    "✅ **Спасибо! Твои ответы записаны.**\n\n"
                    "🔄 Анализирую вашу совместимость...",
                    parse_mode="Markdown"
                )

                # Сразу запускаем анализ для быстрой проверки
                await run_analysis(message, session_id, [answer_partner1, new_answer])
            else:
                await message.answer("❌ Ошибка: не найдены ответы первого партнёра.")
        else:
            # Обычный тест - сохраняем ответы и ждём второго партнёра
            new_answer = Answer(
                session_id=session_id,
                user_id=user_id,
                user_role=role,
                answers=answers
            )
            session.add(new_answer)
            await session.commit()

            await message.answer(
                "✅ **Спасибо! Твои ответы записаны.**\n\n"
                "Ожидай, пока второй партнёр пройдёт тест.",
                parse_mode="Markdown"
            )

            # Проверяем, прошли ли оба партнёра тест
            result = await session.execute(
                select(Answer).where(Answer.session_id == session_id)
            )
            all_answers = result.scalars().all()

            if len(all_answers) == 2:
                # Оба прошли тест, запускаем анализ
                await message.answer("🔄 Оба партнёра прошли тест! Анализирую результаты...")
                await run_analysis(message, session_id, all_answers)

    await state.clear()


async def run_analysis(message: types.Message, session_id: int, all_answers: list):
    """Запуск AI-анализа и отправка результатов"""
    from db.models import Result

    # Получаем ответы партнёров
    answers1 = all_answers[0].answers
    answers2 = all_answers[1].answers
    user1_id = all_answers[0].user_id
    user2_id = all_answers[1].user_id

    # Запускаем AI-анализ
    score, report = await analyze(answers1, answers2)

    async with async_session_maker() as session:
        # Сохраняем результат в БД
        result = Result(
            session_id=session_id,
            compatibility_score=score,
            report=report
        )
        session.add(result)

        # Обновляем статус сессии
        db_session_result = await session.execute(
            select(DBSession).where(DBSession.id == session_id)
        )
        db_session = db_session_result.scalar_one()
        db_session.status = "completed"

        await session.commit()

        # Формируем бесплатный отчёт (ограниченная версия)
        free_report = report[:FREE_REPORT_LIMIT]
        has_full_report = len(report) > FREE_REPORT_LIMIT

        if has_full_report:
            free_report += "\n\n...\n\n💎 **Полный отчёт доступен в премиум-версии**"

        result_message = (
            f"✨ **Ваш результат готов!** ✨\n\n"
            f"💕 **Совместимость: {score}%**\n\n"
            f"{free_report}"
        )

        # Кнопки для upsell
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📖 Хочу полный отчёт", callback_data=f"premium_{session_id}")],
            [InlineKeyboardButton(text="📤 Поделиться результатом",
                                switch_inline_query=f"Мы прошли тест на совместимость! Наш результат: {score}%")]
        ])

        # Отправляем результаты обоим партнёрам
        sent_to = []

        # Отправка первому партнёру
        try:
            await message.bot.send_message(user1_id, result_message, parse_mode="Markdown", reply_markup=keyboard)
            sent_to.append(user1_id)
        except Exception as e:
            print(f"Не удалось отправить партнёру 1 (ID: {user1_id}): {e}")

        # Отправка второму партнёру (если это не тот же пользователь)
        if user2_id != user1_id:
            try:
                await message.bot.send_message(user2_id, result_message, parse_mode="Markdown", reply_markup=keyboard)
                sent_to.append(user2_id)
            except Exception as e:
                print(f"Не удалось отправить партнёру 2 (ID: {user2_id}): {e}")

        # Если никому не удалось отправить, показываем текущему пользователю
        if not sent_to:
            await message.answer(result_message, parse_mode="Markdown", reply_markup=keyboard)
