"""Prepare realistic training dataset for DSPy parser."""

import json
from pathlib import Path

import dspy


# Real-world training examples based on actual use cases
TRAINING_EXAMPLES = [
    # Example 1: Meeting with context
    {
        "message": """Звонила Островской Валерии из IBT. Новости подтвердились. 
        Она в сентябре уходит и будет новый марк дир. Обещала поделиться контактами, 
        чтобы мы могли с ней встретиться - познакомиться""",
        
        "content": "Встретиться с новым директором IBT",
        "description": """Звонила Островской Валерии из IBT. Новости подтвердились. 
Она в сентябре уходит и будет новый марк дир. Обещала поделиться контактами.""",
        
        "entities": ["Островская Валерия", "IBT"],
        "action_type": "встреча",
        "tags": ["встреча", "IBT", "контакты"]
    },
    
    # Example 2: Complex task with list
    {
        "message": """Не обсудили сегодня статус по открытию юр лица:
1. Проработка драфта документов Нестле-WUNDER. Получили ОС от 2 юристов Вундер. Текущие формулировки не подходят под ОКЭД.
2. Подписант. Обсудила с Дарей возможность стать подписантом. Она готова.
3. Учредители. Надо определить список учредителей.
Предлагаю в пт принять финальное решение. Дедлайн: пятница""",
        
        "content": "Обсудить статус открытия юрлица",
        "description": """Не обсудили сегодня статус по открытию юр лица:
1. Проработка драфта документов Нестле-WUNDER. Получили ОС от 2 юристов Вундер. Текущие формулировки не подходят под ОКЭД.
2. Подписант. Обсудила с Дарей возможность стать подписантом. Она готова.
3. Учредители. Надо определить список учредителей.
Предлагаю в пт принять финальное решение.""",
        
        "due_string": "friday",
        "entities": ["Nestle", "WUNDER", "Дарья"],
        "action_type": "решение",
        "tags": ["юрлицо", "документы", "NESTLE", "WUNDER", "срочно"]
    },
    
    # Example 3: Information that becomes a task
    {
        "message": """Удалось вытянуть из нее куда она уходит. В Яндекс. 
        В отдел маркетинга. Сказала ей, что мы как раз выиграли тендер на БТЛ 
        и что нам очень приятно с ней работать. Там и увидимся...""",
        
        "content": "Поддерживать контакт с Яндекс маркетинг",
        "description": """Валерия уходит в Яндекс, в отдел маркетинга. 
Мы выиграли тендер на БТЛ. Сказала что там увидимся.""",
        
        "entities": ["Яндекс", "БТЛ"],
        "action_type": "контакт",
        "tags": ["Яндекс", "маркетинг", "контакты"]
    },
    
    # Example 4: Result report as reminder
    {
        "message": """РА FCB Group Artgroup – 169 баллов
РА Syntez – 151 балл
РА Locals – 38 баллов
РА We Digital – 3 балла
Итого выиграли тендер FCB Group""",
        
        "content": "Связаться с FCB Group по тендеру",
        "description": """Результаты тендера:
РА FCB Group Artgroup – 169 баллов
РА Syntez – 151 балл
РА Locals – 38 баллов
РА We Digital – 3 балла
Победитель: FCB Group""",
        
        "entities": ["FCB Group", "Syntez", "Locals", "We Digital"],
        "action_type": "контакт",
        "tags": ["тендер", "FCB", "контакты"]
    },
    
    # Example 5: Purchase decision with timeline
    {
        "message": """Покупка стоит 5-10 тыс у.е. + время на проверку и риски.
Надо решить до конца недели стоит ли покупать готовое юрлицо или открывать новое.
Плюсы покупки: быстро, уже есть история.
Минусы: риски, дорого, нужна проверка.""",
        
        "content": "Решить: покупать или открывать юрлицо",
        "description": """Покупка стоит 5-10 тыс у.е. + время на проверку и риски.
Плюсы покупки: быстро, уже есть история.
Минусы: риски, дорого, нужна проверка.""",
        
        "due_string": "end of week",
        "entities": [],
        "action_type": "решение",
        "tags": ["юрлицо", "решение", "срочно", "финансы"]
    },
    
    # Example 6: Phone call with follow-up
    {
        "message": """Звонил Петров из Сбера. Интересуется нашим предложением по digital маркетингу.
Просил прислать презентацию и коммерческое предложение до четверга.
Бюджет примерно 2-3 млн руб в месяц. Старт - январь.""",
        
        "content": "Отправить КП Сберу до четверга",
        "description": """Звонил Петров из Сбера. Интересуется digital маркетингом.
Бюджет: 2-3 млн руб/мес. Старт - январь.""",
        
        "due_string": "thursday",
        "entities": ["Петров", "Сбер"],
        "action_type": "документ",
        "tags": ["Сбер", "документы", "КП", "срочно"]
    },
    
    # Example 7: Multi-company coordination
    {
        "message": """Согласование с тремя сторонами:
- Microsoft одобрил бюджет
- Local партнер готов начать в понедельник
- Наша команда ждет финального ТЗ

Нужно собрать всех на созвон завтра в 15:00 по Москве""",
        
        "content": "Созвон по проекту Microsoft завтра 15:00",
        "description": """Согласование с тремя сторонами:
- Microsoft одобрил бюджет
- Local партнер готов начать в понедельник
- Наша команда ждет финального ТЗ""",
        
        "due_string": "tomorrow at 15:00",
        "entities": ["Microsoft"],
        "action_type": "встреча",
        "tags": ["созвон", "Microsoft", "срочно", "встреча"]
    },
    
    # Example 8: Report analysis task
    {
        "message": """Получили отчет от аналитиков. Конверсия упала на 23% за последний месяц.
Основные причины:
1. Технические проблемы на сайте (15%)
2. Изменение алгоритмов рекламы (8%)

Надо разобраться и подготовить план действий к понедельнику.""",
        
        "content": "Подготовить план по конверсии",
        "description": """Конверсия упала на 23% за месяц.
Причины:
1. Технические проблемы на сайте (15%)
2. Изменение алгоритмов рекламы (8%)""",
        
        "due_string": "monday",
        "entities": [],
        "action_type": "документ",
        "tags": ["аналитика", "документы", "срочно", "план"]
    },
    
    # Example 9: Client feedback handling
    {
        "message": """Клиент прислал правки по макетам:
- Логотип сделать крупнее
- Поменять цвет кнопок на фирменный
- Добавить контакты внизу
Просят показать исправленную версию послезавтра утром""",
        
        "content": "Внести правки в макеты для клиента",
        "description": """Правки от клиента:
- Логотип сделать крупнее
- Поменять цвет кнопок на фирменный
- Добавить контакты внизу""",
        
        "due_string": "day after tomorrow morning",
        "entities": [],
        "action_type": "работа",
        "tags": ["дизайн", "правки", "срочно"]
    },
    
    # Example 10: Team coordination
    {
        "message": """Маша в отпуске до 15 числа. Ее задачи по проекту Х5:
- Отчет по трафику (критично!)
- Встреча с подрядчиком во вторник
- Презентация результатов в среду

Нужно распределить между командой""",
        
        "content": "Распределить задачи Маши по X5",
        "description": """Маша в отпуске до 15 числа. Ее задачи:
- Отчет по трафику (критично!)
- Встреча с подрядчиком во вторник
- Презентация результатов в среду""",
        
        "entities": ["Маша", "X5"],
        "action_type": "решение",
        "tags": ["X5", "команда", "срочно", "решение"]
    }
]


def create_dspy_examples():
    """Convert training data to DSPy examples."""
    examples = []
    
    for data in TRAINING_EXAMPLES:
        # Create example with all fields
        example = dspy.Example(
            message=data["message"],
            content=data["content"],
            description=data.get("description", ""),
            due_string=data.get("due_string", None),
            entities=data.get("entities", []),
            action_type=data.get("action_type", ""),
            tags=data.get("tags", [])
        ).with_inputs("message")
        
        examples.append(example)
    
    return examples


def save_dataset(examples, filepath="data/dspy_training_data.json"):
    """Save examples to JSON file."""
    # Create data directory if not exists
    Path(filepath).parent.mkdir(exist_ok=True)
    
    # Convert to serializable format
    serializable_data = []
    for ex in examples:
        serializable_data.append({
            "message": ex.message,
            "content": ex.content,
            "description": ex.description,
            "due_string": ex.due_string,
            "entities": ex.entities,
            "action_type": ex.action_type,
            "tags": ex.tags
        })
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(serializable_data, f, ensure_ascii=False, indent=2)
    
    print(f"Saved {len(serializable_data)} examples to {filepath}")


def load_dataset(filepath="data/dspy_training_data.json"):
    """Load examples from JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    examples = []
    for item in data:
        example = dspy.Example(
            message=item["message"],
            content=item["content"],
            description=item["description"],
            due_string=item["due_string"],
            entities=item["entities"],
            action_type=item["action_type"],
            tags=item["tags"]
        ).with_inputs("message")
        examples.append(example)
    
    return examples


if __name__ == "__main__":
    # Create DSPy examples
    examples = create_dspy_examples()
    print(f"Created {len(examples)} training examples")
    
    # Save to file
    save_dataset(examples)
    
    # Test loading
    loaded_examples = load_dataset()
    print(f"Loaded {len(loaded_examples)} examples")
    
    # Show first example
    if loaded_examples:
        ex = loaded_examples[0]
        print("\nFirst example:")
        print(f"Message: {ex.message[:100]}...")
        print(f"Content: {ex.content}")
        print(f"Tags: {ex.tags}")