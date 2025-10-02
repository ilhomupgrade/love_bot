# ❤️ LoveBot - Telegram Bot для проверки совместимости

Telegram-бот для анализа совместимости партнёров на основе языков любви с использованием AI.

## 🎯 Возможности

- 🔗 Создание сессии для двух партнёров
- 📝 Прохождение теста на языки любви (5 вопросов)
- 🤖 AI-анализ совместимости через OpenAI GPT
- 📊 Индекс совместимости (0-100%)
- 💎 Бесплатная и премиум версии отчёта
- 💾 Хранение результатов в базе данных

## 🛠 Технологический стек

- **Python 3.11+**
- **Aiogram 3.x** - фреймворк для Telegram-ботов
- **SQLAlchemy** - ORM для работы с БД
- **SQLite** - база данных (легко заменить на PostgreSQL)
- **OpenAI API** - GPT-4/5 для анализа

## 📂 Структура проекта

```
lovebot/
├── bot.py                 # основной запуск бота
├── config.py              # настройки (токены, БД)
├── handlers/              # обработчики команд
│   ├── start.py          # /start, присоединение к сессии
│   ├── test.py           # прохождение теста
│   └── results.py        # просмотр результатов
├── db/
│   ├── database.py       # подключение к БД
│   └── models.py         # SQLAlchemy модели
├── services/
│   ├── analyzer.py       # AI-анализ
│   └── utils.py          # вспомогательные функции
├── requirements.txt
├── .env.example
└── README.md
```

## 🚀 Установка и запуск

### 1. Клонирование репозитория

```bash
cd love-bot-v1
```

### 2. Создание виртуального окружения

```bash
python3 -m venv venv
source venv/bin/activate  # на Windows: venv\Scripts\activate
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Настройка окружения

Скопируй `.env.example` в `.env` и заполни данные:

```bash
cp .env.example .env
```

Отредактируй `.env`:

```env
BOT_TOKEN=your-telegram-bot-token-here
OPENAI_API_KEY=your-openai-api-key-here
DATABASE_URL=sqlite+aiosqlite:///./lovebot.db
```

**Где получить токены:**
- `BOT_TOKEN`: создай бота через [@BotFather](https://t.me/BotFather)
- `OPENAI_API_KEY`: получи на [platform.openai.com](https://platform.openai.com)

### 5. Запуск бота

```bash
python bot.py
```

## 📱 Использование

### Основные команды:

- `/start` - Создать новую сессию
- `/test` - Пройти тест на совместимость
- `/results` - Показать результаты последнего теста
- `/premium` - Получить полный отчёт
- `/help` - Справка по командам

### Процесс работы:

1. **Партнёр 1** отправляет `/start` боту
2. Бот создаёт сессию и выдаёт ссылку для **Партнёра 2**
3. **Партнёр 2** отправляет ссылку `/join_123_partner2`
4. Оба партнёра проходят тест командой `/test`
5. После завершения оба получают результаты автоматически

## 🗄 Модель базы данных

### Session (Сессия)
- `id` - уникальный ID
- `created_at` - дата создания
- `status` - статус (pending, in_progress, completed)
- `partner1_user_id` - Telegram ID первого партнёра
- `partner2_user_id` - Telegram ID второго партнёра

### Answer (Ответы)
- `id` - уникальный ID
- `session_id` - ID сессии
- `user_id` - Telegram ID пользователя
- `user_role` - роль (partner1 или partner2)
- `answers` - JSON с ответами
- `completed_at` - дата завершения

### Result (Результаты)
- `id` - уникальный ID
- `session_id` - ID сессии
- `compatibility_score` - индекс совместимости (0-100)
- `report` - полный отчёт от AI
- `created_at` - дата создания

## 🔧 Настройка для продакшена

### Переход на PostgreSQL

В `.env` замени:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost/lovebot
```

Установи драйвер:

```bash
pip install asyncpg
```

### Запуск через systemd (Linux)

Создай файл `/etc/systemd/system/lovebot.service`:

```ini
[Unit]
Description=LoveBot Telegram Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/lovebot
ExecStart=/path/to/venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Запусти:

```bash
sudo systemctl enable lovebot
sudo systemctl start lovebot
```

## 📊 Примеры вопросов теста

1. Что для тебя важнее в отношениях?
   - A) Проводить много времени вместе ⏰
   - B) Получать подарки и сюрпризы 🎁
   - C) Слышать слова любви и комплименты 💬
   - D) Помощь и поддержка в делах 🤝
   - E) Физическая близость и прикосновения 🤗

*(всего 5 вопросов)*

## 🤖 AI-анализ

Бот использует OpenAI GPT для анализа ответов и генерирует:

1. **Индекс совместимости** (0-100%)
2. **Языки любви** каждого партнёра
3. **Потенциальные трудности**
4. **Рекомендации** для улучшения отношений
5. **Образное описание** пары

## 💎 Монетизация

- **Бесплатная версия**: первые 500 символов отчёта
- **Премиум**: полный отчёт через `/premium`

*(в текущей версии премиум бесплатный, добавь платёжную систему по необходимости)*

## 📝 TODO

- [ ] Интеграция платёжной системы (Telegram Payments / YooKassa)
- [ ] Добавить больше вопросов
- [ ] Многоязычная поддержка
- [ ] Графики совместимости
- [ ] История всех тестов пользователя
- [ ] Рекомендации на основе архетипов

## 🐛 Известные проблемы

- Нет обработки истёкших сессий (>24 часа)
- Нет ограничения на количество сессий одного пользователя
- AI может генерировать слишком длинные отчёты

## 🤝 Вклад в проект

Pull requests приветствуются! Для больших изменений сначала создай issue.

## 📄 Лицензия

MIT

## 📧 Контакты

Вопросы и предложения: [@your_username](https://t.me/your_username)
