# Тренажер для подготовки к экзамену (GigaChat + FastAPI)

Приложение генерирует случайные задачи по дискретной математике и матанализу с помощью GigaChat API на основе базы знаний `syllabus.md`.

## Для кого
Для студентов, готовящихся к экзамену по математике.

## Установка
1. Клонируйте репозиторий.
2. Создайте окружение: `python -m venv venv`
3. Активируйте: `source venv/bin/activate` (или `venv\Scripts\activate` на Windows).
4. Установите зависимости: `pip install -r requirements.txt`
5. Создайте `.env` на основе `.env.example` и вставьте ваш `GIGACHAT_AUTH_KEY`.

## Запуск
Запустите сервер (без флага `--reload` для продакшена):
```bash
uvicorn app:app --host 0.0.0.0 --port 8000