# Todoist API v1 Integration Guide для TaskerBot

## TL;DR для рекламного агентства

Todoist перешел на **unified API v1** в 2024. Старые REST API v2 и Sync API v9 deprecated. Новый API работает по принципу "sync + commands" с rate limit 1000 requests/15 минут.

**Главное для TaskerBot**: Используй команды для создания задач, sync_token для получения обновлений, personal token для аутентификации команды.

---

## Современное состояние Todoist API (2024-2025)

### Какой API использовать

❌ **НЕ используй:**
- REST API v2 (deprecated)
- Sync API v9 (deprecated) 
- Старый Python SDK `todoist-python` (deprecated)

✅ **Используй:**
- **Unified Todoist API v1** — актуальный API
- Новый Python SDK `todoist-api-python` или прямые HTTP запросы
- JavaScript SDK `todoist-api-typescript`

### Основные характеристики API v1

```
Endpoint: https://api.todoist.com/api/v1/sync
Метод: POST
Аутентификация: Bearer Token
Content-Type: application/json
Rate Limit: 1000 requests / 15 минут / пользователь
```

---

## Аутентификация

### Personal Token (единственный метод аутентификации)

1. Каждый пользователь заходит в Todoist → Settings → Integrations
2. Копирует Personal Token
3. Вводит токен в боте через команду /setup
4. Токен шифруется и сохраняется в базе данных
5. Используется в заголовке: `Authorization: Bearer USER_TOKEN`

**Важно**: Мы НЕ используем OAuth! Только Personal Tokens, которые каждый пользователь вводит сам.

---

## Базовая структура API v1

### Sync Request

```python
import requests

def todoist_sync(token, sync_token="*", resource_types=None, commands=None):
    url = "https://api.todoist.com/api/v1/sync"
    
    data = {
        "sync_token": sync_token,
        "resource_types": resource_types or ["all"],
    }
    
    if commands:
        data["commands"] = commands
        
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, json=data, headers=headers)
    return response.json()
```

### Sync Response Structure

```json
{
  "sync_token": "новый_токен_для_следующего_запроса",
  "full_sync": true,
  "projects": [...],
  "items": [...],
  "labels": [...],
  "user": {...},
  "temp_id_mapping": {...}
}
```

---

## Практические примеры для TaskerBot

### 1. Получение всех проектов

```python
def get_all_projects(token):
    """Получить все проекты пользователя"""
    result = todoist_sync(
        token=token,
        resource_types=["projects"]
    )
    return result.get("projects", [])

# Пример использования
projects = get_all_projects("your_token_here")
for project in projects:
    print(f"ID: {project['id']}, Name: {project['name']}")
```

### 2. Создание задачи через команды

```python
import uuid
from datetime import datetime

def create_task(token, content, project_id=None, due_date=None, priority=1):
    """Создать новую задачу"""
    
    command = {
        "type": "item_add",
        "temp_id": str(uuid.uuid4()),
        "uuid": str(uuid.uuid4()),
        "args": {
            "content": content,
            "priority": priority
        }
    }
    
    # Добавить проект если указан
    if project_id:
        command["args"]["project_id"] = project_id
        
    # Добавить дату если указана
    if due_date:
        command["args"]["due"] = {
            "date": due_date.strftime("%Y-%m-%d")
        }
    
    result = todoist_sync(
        token=token,
        commands=[command]
    )
    
    return result

# Пример использования
task = create_task(
    token="your_token",
    content="Созвониться с клиентом по кампании",
    due_date=datetime.now()
)
```

### 3. TaskerBot Integration Class

```python
import re
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class TodoistClient:
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.todoist.com/api/v1/sync"
        self.sync_token = "*"  # "*" для full sync
        
    def _make_request(self, resource_types=None, commands=None):
        """Базовый метод для запросов"""
        data = {"sync_token": self.sync_token}
        
        if resource_types:
            data["resource_types"] = resource_types
        if commands:
            data["commands"] = commands
            
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(self.base_url, json=data, headers=headers)
        result = response.json()
        
        # Обновляем sync_token для инкрементальных синков
        if "sync_token" in result:
            self.sync_token = result["sync_token"]
            
        return result
    
    def get_projects(self) -> List[Dict]:
        """Получить все проекты"""
        result = self._make_request(resource_types=["projects"])
        return result.get("projects", [])
    
    def get_inbox_project_id(self) -> str:
        """Получить ID проекта Inbox"""
        projects = self.get_projects()
        for project in projects:
            if project.get("is_inbox_project"):
                return project["id"]
        return None
    
    def create_task_from_voice(self, voice_text: str, project_name: str = None) -> Dict:
        """
        Создать задачу из голосового сообщения
        Применяет AI обработку для извлечения контекста
        """
        
        # Парсинг приоритета из голоса
        priority = self._extract_priority(voice_text)
        
        # Парсинг даты
        due_date = self._extract_due_date(voice_text)
        
        # Определение проекта
        project_id = self._get_project_id(project_name) if project_name else self.get_inbox_project_id()
        
        # Очистка текста от временных меток
        clean_content = self._clean_voice_content(voice_text)
        
        command = {
            "type": "item_add",
            "temp_id": str(uuid.uuid4()),
            "uuid": str(uuid.uuid4()),
            "args": {
                "content": clean_content,
                "project_id": project_id,
                "priority": priority
            }
        }
        
        if due_date:
            command["args"]["due"] = {"date": due_date.strftime("%Y-%m-%d")}
            
        result = self._make_request(commands=[command])
        return result
    
    def _extract_priority(self, text: str) -> int:
        """Извлечь приоритет из текста"""
        text_lower = text.lower()
        if any(word in text_lower for word in ["срочно", "важно", "критично"]):
            return 4  # Высший приоритет
        elif any(word in text_lower for word in ["приоритет", "скоро"]):
            return 3
        return 1  # Обычный приоритет
    
    def _extract_due_date(self, text: str) -> Optional[datetime]:
        """Извлечь дату из текста"""
        text_lower = text.lower()
        today = datetime.now().date()
        
        if "сегодня" in text_lower:
            return datetime.combine(today, datetime.min.time())
        elif "завтра" in text_lower:
            return datetime.combine(today + timedelta(days=1), datetime.min.time())
        elif "послезавтра" in text_lower:
            return datetime.combine(today + timedelta(days=2), datetime.min.time())
        elif "на следующей неделе" in text_lower:
            return datetime.combine(today + timedelta(days=7), datetime.min.time())
            
        # Парсинг конкретных дат (можно расширить)
        date_pattern = r"(\d{1,2})\.(\d{1,2})"
        match = re.search(date_pattern, text)
        if match:
            day, month = int(match.group(1)), int(match.group(2))
            try:
                return datetime(today.year, month, day)
            except ValueError:
                pass
                
        return None
    
    def _clean_voice_content(self, text: str) -> str:
        """Очистить голосовой текст от временных меток"""
        # Убираем временные слова
        temporal_words = ["сегодня", "завтра", "послезавтра", "срочно", "важно"]
        words = text.split()
        cleaned_words = [word for word in words if word.lower() not in temporal_words]
        return " ".join(cleaned_words).strip()
    
    def _get_project_id(self, project_name: str) -> str:
        """Получить ID проекта по имени"""
        if not project_name:
            return self.get_inbox_project_id()
            
        projects = self.get_projects()
        for project in projects:
            if project["name"].lower() == project_name.lower():
                return project["id"]
                
        return self.get_inbox_project_id()  # Fallback к Inbox
    
    def get_tasks(self, project_id: str = None) -> List[Dict]:
        """Получить задачи"""
        result = self._make_request(resource_types=["items"])
        items = result.get("items", [])
        
        if project_id:
            items = [item for item in items if item.get("project_id") == project_id]
            
        return items
    
    def complete_task(self, task_id: str) -> Dict:
        """Отметить задачу как выполненную"""
        command = {
            "type": "item_complete",
            "uuid": str(uuid.uuid4()),
            "args": {
                "id": task_id
            }
        }
        
        return self._make_request(commands=[command])
```

### 4. Интеграция с TaskerBot

```python
# bot.py
from todoist_client import TodoistClient

class TaskerBot:
    def __init__(self, telegram_token: str, todoist_token: str):
        self.bot = telebot.TeleBot(telegram_token)
        self.todoist = TodoistClient(todoist_token)
        self.setup_handlers()
    
    def setup_handlers(self):
        
        @self.bot.message_handler(content_types=['voice'])
        def handle_voice(message):
            # 1. Транскрипция через Deepgram
            voice_text = self.transcribe_voice(message.voice.file_id)
            
            # 2. AI обработка через OpenAI
            structured_task = self.process_with_ai(voice_text, message.from_user.id)
            
            # 3. Создание задачи в Todoist
            result = self.todoist.create_task_from_voice(
                voice_text=structured_task["content"],
                project_name=structured_task.get("project")
            )
            
            # 4. Ответ пользователю
            if "temp_id_mapping" in result:
                self.bot.reply_to(message, f"✅ Задача создана: {structured_task['content']}")
            else:
                self.bot.reply_to(message, "❌ Ошибка при создании задачи")
        
        @self.bot.message_handler(commands=['tasks'])
        def show_tasks(message):
            tasks = self.todoist.get_tasks()
            if tasks:
                task_list = "\n".join([f"• {task['content']}" for task in tasks[:10]])
                self.bot.reply_to(message, f"Твои задачи:\n{task_list}")
            else:
                self.bot.reply_to(message, "Нет активных задач")
    
    def process_with_ai(self, voice_text: str, user_id: int) -> Dict:
        """Обработка голосового текста через OpenAI"""
        
        # Контекст рекламного агентства для AI
        agency_context = """
        Контекст: Рекламное агентство с разными департаментами.
        Роли: аккаунт-менеджеры, топ-менеджеры, SMM-менеджеры, продюсеры, ивентеры.
        Проекты: клиентские кампании, внутренние задачи, креативы, ивенты.
        Типовые задачи: звонки клиентам, подготовка презентаций, запуск рекламы, организация мероприятий.
        """
        
        prompt = f"""
        {agency_context}
        
        Голосовое сообщение: "{voice_text}"
        
        Извлеки из текста:
        1. Основную задачу (что нужно сделать)
        2. Проект/клиент (если упоминается)
        3. Приоритет (если есть слова "срочно", "важно")
        4. Дату (если упоминается время)
        5. Тип задачи (звонок, встреча, креатив, отчет, ивент)
        
        Ответь в JSON:
        {{
            "content": "очищенный текст задачи",
            "project": "название проекта/клиента или null",
            "priority": 1-4,
            "due_date": "YYYY-MM-DD или null",
            "task_type": "тип задачи"
        }}
        """
        
        # Вызов OpenAI API
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
```

---

## Специфика для рекламного агентства

### Типовые проекты и задачи

```python
# Шаблоны задач для разных ролей в агентстве
AGENCY_TASK_TEMPLATES = {
    "account_manager": [
        "Звонок клиенту {client}",
        "Подготовить отчет по кампании {campaign}",
        "Встреча с {client} по новому проекту",
        "Обсудить бюджет на {month} с {client}"
    ],
    "smm_manager": [
        "Запустить рекламу в {platform}",
        "Подготовить контент-план на {period}",
        "Аналитика по постам за {period}",
        "Модерация комментариев {client}"
    ],
    "producer": [
        "Организовать съемку для {client}",
        "Забрифовать команду по проекту {project}",
        "Контроль дедлайнов по {campaign}",
        "Координация с подрядчиками"
    ],
    "event_manager": [
        "Подготовка площадки для ивента {event}",
        "Координация с кейтерингом",
        "Брифинг технической команды",
        "Пост-ивент аналитика"
    ],
    "creative": [
        "Разработать креатив для {campaign}",
        "Ревизия макетов от дизайнера",
        "Подготовить презентацию концепции",
        "Адаптация креатива под {platform}"
    ]
}

def detect_role_and_suggest_template(voice_text: str) -> str:
    """Определить роль и предложить шаблон задачи"""
    
    role_keywords = {
        "account_manager": ["клиент", "отчет", "бюджет", "встреча"],
        "smm_manager": ["пост", "реклама", "контент", "аналитика"],
        "producer": ["съемка", "команда", "дедлайн", "координация"],
        "event_manager": ["ивент", "мероприятие", "площадка", "кейтеринг"],
        "creative": ["креатив", "дизайн", "макет", "концепция"]
    }
    
    text_lower = voice_text.lower()
    
    for role, keywords in role_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            return role
            
    return "general"
```

### Автоматическое определение проектов

```python
def extract_client_project(voice_text: str) -> Dict:
    """Извлечь клиента и проект из голосового сообщения"""
    
    # Паттерны для определения клиентов
    client_patterns = [
        r"для\s+([А-Я][а-я]+)",  # "для Яндекса"
        r"по\s+([А-Я][а-я]+)",   # "по проекту Сбербанк"
        r"клиент\s+([А-Я][а-я]+)",  # "клиент Тинькофф"
        r"кампани[ия]\s+([А-Я][а-я]+)"  # "кампания МТС"
    ]
    
    for pattern in client_patterns:
        match = re.search(pattern, voice_text)
        if match:
            return {
                "client": match.group(1),
                "project_name": f"Клиент: {match.group(1)}"
            }
    
    return {"client": None, "project_name": None}
```

---

## Rate Limits и оптимизация

### Лимиты

- **1000 requests / 15 минут** на пользователя
- Для агентства 20 человек = ~50 requests/15 минут на человека
- Достаточно для нормального использования

### Оптимизация

```python
import time
from functools import wraps

def rate_limit(max_calls=50, time_window=900):  # 50 calls per 15 minutes
    calls = []
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            # Удаляем старые вызовы
            calls[:] = [call_time for call_time in calls if now - call_time < time_window]
            
            if len(calls) >= max_calls:
                sleep_time = time_window - (now - calls[0]) + 1
                time.sleep(sleep_time)
                
            calls.append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Применение
@rate_limit(max_calls=50, time_window=900)
def create_task_safe(self, content):
    return self.create_task_from_voice(content)
```

### Кэширование sync_token

```python
import redis

class TodoistClientCached(TodoistClient):
    def __init__(self, token: str):
        super().__init__(token)
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.cache_key = f"todoist_sync_token:{token[:8]}"
        
        # Загружаем сохраненный sync_token
        cached_token = self.redis_client.get(self.cache_key)
        if cached_token:
            self.sync_token = cached_token.decode()
    
    def _make_request(self, resource_types=None, commands=None):
        result = super()._make_request(resource_types, commands)
        
        # Сохраняем sync_token в Redis
        if "sync_token" in result:
            self.redis_client.setex(
                self.cache_key, 
                3600,  # 1 час TTL
                result["sync_token"]
            )
            
        return result
```

---

## Error Handling

### Основные коды ошибок

```python
class TodoistAPIError(Exception):
    pass

def handle_todoist_response(response):
    """Обработка ответов Todoist API"""
    
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 400:
        raise TodoistAPIError("Неверный запрос")
    elif response.status_code == 401:
        raise TodoistAPIError("Неверный токен")
    elif response.status_code == 403:
        raise TodoistAPIError("Нет доступа")
    elif response.status_code == 429:
        raise TodoistAPIError("Превышен rate limit")
    elif response.status_code >= 500:
        raise TodoistAPIError("Ошибка сервера Todoist")
    else:
        raise TodoistAPIError(f"Неизвестная ошибка: {response.status_code}")

# Retry logic
import time
import random

def retry_on_failure(max_retries=3, backoff_factor=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except TodoistAPIError as e:
                    if "rate limit" in str(e) and attempt < max_retries - 1:
                        sleep_time = backoff_factor * (2 ** attempt) + random.uniform(0, 1)
                        time.sleep(sleep_time)
                        continue
                    raise
            return None
        return wrapper
    return decorator
```

---

## Deployment и мониторинг

### Environment Variables

```bash
# .env
TODOIST_TOKEN=your_personal_token_here
TELEGRAM_TOKEN=your_bot_token_here
OPENAI_API_KEY=your_openai_key_here
DEEPGRAM_API_KEY=your_deepgram_key_here

# Для продакшена
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=INFO
```

### Логирование

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('taskerbot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# В коде
try:
    result = todoist.create_task_from_voice(voice_text)
    logger.info(f"Task created successfully: {result.get('temp_id_mapping')}")
except TodoistAPIError as e:
    logger.error(f"Todoist API error: {e}")
    # Отправить уведомление админу
```

### Мониторинг rate limits

```python
def monitor_rate_limits(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            logger.info(f"API call successful, took {time.time() - start_time:.2f}s")
            return result
        except TodoistAPIError as e:
            if "rate limit" in str(e):
                logger.warning(f"Rate limit hit after {time.time() - start_time:.2f}s")
                # Уведомить админа в Telegram
            raise
    return wrapper
```

---

## Заключение

Todoist unified API v1 отлично подходит для TaskerBot в рекламном агентстве. Ключевые преимущества:

✅ **Современный API** — поддерживается и развивается  
✅ **Commands-based** — идеально для пакетных операций  
✅ **Sync tokens** — эффективная синхронизация  
✅ **Rate limits** — достаточно для команды агентства  
✅ **Real-time** — можно добавить webhooks позже  

Начинай с простого: personal token + создание задач из голоса. Потом добавишь проекты клиентов, автоматическое определение ролей и аналитику.

**Next steps:**
1. Реализуй `TodoistClient` класс
2. Интегрируй с Deepgram + OpenAI  
3. Добавь контекст ролей агентства
4. Тестируй на части команды
5. Мониторинг и оптимизация
