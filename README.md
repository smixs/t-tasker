# 🎯 T-Tasker - Telegram-бот для Todoist из текста или голоса

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue.svg" alt="Python 3.12">
  <img src="https://img.shields.io/badge/Telegram-Bot%20API-blue.svg" alt="Telegram Bot API">
  <img src="https://img.shields.io/badge/Todoist-REST%20API-red.svg" alt="Todoist API">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/Code-Open%20Source-success.svg" alt="Open Source">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED.svg" alt="Docker Ready">
</p>

## 🚀 Основные возможности

- **🎤 Голосовые сообщения** - Надиктуйте задачу, бот распознает и создаст её в Todoist
- **💬 Текстовые сообщения** - Пишите задачи естественным языком
- **🧠 Умный парсинг** - Автоматически извлекает дату, приоритет, проект и метки
- **🌍 Мультиязычность** - Поддержка русского и английского языков
- **🔐 Персональные токены** - Каждый пользователь использует свой Todoist API токен
- **⚡ Быстрая работа** - Создание задачи менее чем за 4 секунды
- **🗑️ Автоудаление** - Опция автоматического удаления предыдущей задачи

## 📋 Системные требования

- Docker и Docker Compose
- 1GB RAM минимум
- 2GB свободного места на диске
- Доступ в интернет для внешних API

### API ключи (нужны ваши собственные)

1. **Telegram Bot Token** - Получите у [@BotFather](https://t.me/botfather)
2. **OpenAI API Key** - Создайте на [platform.openai.com](https://platform.openai.com)
3. **Deepgram API Key** - Получите на [deepgram.com](https://deepgram.com)
4. **Todoist Personal Token** - Каждый пользователь вводит свой через команду `/setup`

## 🐳 Быстрый запуск с Docker (рекомендуется)

### 1. Клонирование репозитория

```bash
git clone https://github.com/your-repo/t-tasker.git
cd t-tasker
```

### 2. Настройка переменных окружения

```bash
cp .env.example .env
```

Отредактируйте `.env` файл и добавьте ваши ключи:

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_FROM_BOTFATHER
TELEGRAM_WEBHOOK_URL=https://your-domain.com  # Опционально

# OpenAI (для парсинга задач)
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
OPENAI_MODEL=gpt-4o-2024-11-20

# Deepgram (для распознавания речи)
DEEPGRAM_API_KEY=YOUR_DEEPGRAM_API_KEY

# Безопасность - ОБЯЗАТЕЛЬНО сгенерируйте новые!
ENCRYPTION_KEY=GENERATE_NEW_KEY_SEE_BELOW
SESSION_SECRET=YOUR_RANDOM_SECRET_STRING

# База данных (для Docker Compose не меняйте)
DATABASE_URL=postgresql+asyncpg://taskerbot:password@postgres:5432/taskerbot
```

### 3. Генерация ключа шифрования

```python
# Запустите этот Python код для генерации ключа
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(f"ENCRYPTION_KEY={key.decode()}")
```

### 4. Запуск всех сервисов

```bash
# Запустить все контейнеры
docker compose up -d

# Проверить статус
docker compose ps

# Посмотреть логи
docker compose logs -f bot
```

Бот автоматически запустится вместе с PostgreSQL и Redis в изолированных контейнерах.

## 💻 Локальный запуск для разработки

### 1. Установка зависимостей

```bash
# Установка uv (менеджер пакетов Python)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Установка зависимостей проекта
uv sync
```

### 2. Запуск только базы данных

```bash
# Запустить PostgreSQL и Redis
make db

# Или через docker compose
docker compose up -d postgres redis
```

### 3. Запуск бота локально

```bash
# В режиме polling (для разработки)
make run

# Или напрямую
uv run python run_simple.py
```

## 📱 Использование бота

### Первоначальная настройка

1. Найдите вашего бота в Telegram: `@your_bot_name`
2. Отправьте команду `/start`
3. Нажмите кнопку "🔐 Авторизоваться в Todoist"
4. Следуйте инструкции для получения Personal Token:

<img src="assets/images/todoist_api_token_guide.png" alt="Todoist API Token Guide" width="600">

5. Отправьте токен боту (он будет зашифрован и сохранен)
6. Готово! Теперь можно создавать задачи

### Примеры использования

**Голосовое сообщение:**
- "Встретиться с клиентом завтра в 15:00"
- "Купить молоко сегодня вечером"

**Текстовое сообщение:**
- "Позвонить маме завтра утром #семья p2"
- "Закончить отчет до пятницы @работа"

### Доступные команды

- `/start` - Начать работу с ботом
- `/help` - Показать справку
- `/setup` - Настроить или обновить Todoist токен
- `/recent` - Показать последние созданные задачи
- `/undo` - Отменить последнюю задачу
- `/autodelete` - Включить/выключить автоудаление предыдущей задачи
- `/cancel` - Отменить текущую операцию

## 🏗️ Архитектура проекта

### Структура файлов

```
t-tasker/
├── src/
│   ├── core/           # Ядро приложения
│   │   ├── bot.py      # Инициализация бота
│   │   ├── database.py # Подключение к БД
│   │   ├── settings.py # Конфигурация
│   │   └── middleware/ # Middleware для безопасности
│   ├── handlers/       # Обработчики сообщений
│   ├── services/       # Внешние сервисы
│   │   ├── openai_service.py   # GPT-4 парсинг
│   │   ├── deepgram_service.py # Распознавание речи
│   │   ├── todoist_service.py  # Todoist API
│   │   └── encryption.py       # Шифрование данных
│   └── models/         # Модели данных
├── docker-compose.yml  # Docker конфигурация
├── Dockerfile         # Сборка образа
└── Makefile          # Удобные команды
```

### Технологический стек

- **Python 3.12** - Основной язык
- **aiogram 3.21** - Telegram Bot framework
- **PostgreSQL 16** - База данных
- **Redis 7** - Кеширование (опционально)
- **Docker** - Контейнеризация
- **OpenAI GPT-4** - Обработка естественного языка
- **Deepgram Nova-3** - Распознавание речи

### Изоляция в Docker

```dockerfile
# Используется не-root пользователь
USER appuser

# Минимальный базовый образ
FROM python:3.12-slim

# Только необходимые зависимости
# Размер образа < 120MB
```

## 🔧 Разработка и тестирование

### Полезные команды

```bash
# Тестирование
make test          # Запуск всех тестов
make test-cov      # Тесты с покрытием

# Качество кода
make lint          # Проверка линтером
make typecheck     # Проверка типов

# Docker операции
make docker-build  # Сборка образа
make docker-logs   # Просмотр логов
make docker-shell  # Вход в контейнер
```

### Переменные окружения

Все чувствительные данные хранятся в `.env` файле, который **НЕ** должен попадать в git:

- `.env` - Ваши реальные ключи (в .gitignore)
- `.env.example` - Пример с описанием всех переменных
- `.env.docker` - Дополнительные настройки для Docker (опционально)

## 📊 Производительность и мониторинг

### Метрики производительности

- ⚡ Распознавание голоса: 2-3 секунды
- 🚀 Создание задачи: <1 секунды
- 📊 Общая задержка: <4 секунд
- 💾 Использование памяти: ~100MB
- 🔌 Пул соединений к БД: 10

### Health Check

Endpoint для проверки здоровья: `GET /health`

```json
{
  "status": "healthy",
  "timestamp": "2025-01-19T12:00:00Z",
  "version": "1.0.0",
  "services": {
    "database": "ok",
    "redis": "ok",
    "telegram": "ok"
  }
}
```

## 🛡️ Дополнительные меры безопасности

1. **Регулярно обновляйте зависимости:**
   ```bash
   uv lock --upgrade
   docker compose pull
   ```

2. **Используйте сильные пароли для БД** - Измените стандартные пароли в docker-compose.yml

3. **Ограничьте доступ к портам** - Используйте firewall для ограничения доступа

4. **Резервное копирование:**
   ```bash
   make backup-db  # Создает backup БД
   ```

5. **Логирование** - Все операции логируются для аудита

## 🤝 Вклад в проект

Мы приветствуем вклад в развитие проекта!

1. Форкните репозиторий
2. Создайте ветку (`git checkout -b feature/amazing-feature`)
3. Коммитьте изменения (`git commit -m 'Add amazing feature'`)
4. Пушьте ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📝 Лицензия

Этот проект лицензирован под MIT License - полностью открытая лицензия, позволяющая свободное использование, модификацию и распространение.

См. файл [LICENSE](LICENSE) для деталей.

## ❓ Часто задаваемые вопросы

**Q: Безопасно ли вводить мой Todoist токен?**
A: Да, токен шифруется перед сохранением и хранится только в вашей базе данных.

**Q: Можно ли запустить бота без Docker?**
A: Да, см. раздел "Локальный запуск для разработки".

**Q: Какие данные собирает бот?**
A: Только те, что необходимы для работы: ваш Telegram ID, зашифрованный Todoist токен и ID созданных задач.

**Q: Можно ли использовать другую БД вместо PostgreSQL?**
A: Технически да, но потребуется изменение кода. PostgreSQL рекомендуется.

**Q: Поддерживается ли self-hosted Todoist?**
A: Нет, только официальный Todoist API.

## 🆘 Поддержка

- Создайте [Issue](https://github.com/your-repo/t-tasker/issues) для багов
- Discussions для вопросов и предложений
- Wiki для дополнительной документации

---

<p align="center">
  Сделано с ❤️ для продуктивных людей, которые ценят приватность
</p>
