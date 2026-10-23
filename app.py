import os
import uuid
import json
import logging
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Math Exam Trainer")

# Подключаем статику для фронтенда
app.mount("/static", StaticFiles(directory="static"), name="static")

# Конфигурация
APP_VERSION = "1.0.0"
GIGACHAT_AUTH_KEY = os.getenv("GIGACHAT_AUTH_KEY")
GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")


# Модель для запроса генерации
class GenerateRequest(BaseModel):
    topic: str | None = None


# --- Чтение базы знаний ---
def get_syllabus():
    try:
        with open("syllabus.md", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error("syllabus.md not found!")
        return "База знаний не найдена."


# --- Работа с GigaChat API ---
async def get_gigachat_token():
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "RqUID": str(uuid.uuid4()),
        "Authorization": f"Basic {GIGACHAT_AUTH_KEY}"
    }
    data = {"scope": GIGACHAT_SCOPE}

    async with httpx.AsyncClient(verify=False) as client:  # verify=False для обхода проблем с сертификатами Сбера
        response = await client.post(url, headers=headers, data=data)
        if response.status_code != 200:
            logger.error(f"Failed to get token: {response.text}")
            raise HTTPException(status_code=500, detail="Ошибка авторизации GigaChat")
        return response.json()["access_token"]


async def generate_question_from_ai(topic_context: str):
    token = await get_gigachat_token()
    url = "https://api.giga.chat/v1/chat/completions"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    Ты — преподаватель. На основе следующих тем сгенерируй ОДНУ простую задачу:
    {topic_context}

    Верни ответ СТРОГО в формате JSON без лишних символов:
    {{
        "task": "Текст задачи",
        "options": ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
        "correct_index": 0
    }}
    где correct_index — это индекс правильного ответа от 0 до 3.
    """

    payload = {
        "model": "GigaChat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "response_format": {
            "type": "json_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "task": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                    "correct_index": {"type": "integer"}
                },
                "required": ["task", "options", "correct_index"]
            }
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=30.0)
        if response.status_code != 200:
            logger.error(f"GigaChat error: {response.text}")
            raise HTTPException(status_code=500, detail="Ошибка генерации задачи")

        content = response.json()["choices"][0]["message"]["content"]
        logger.info("Successfully generated task from GigaChat")
        return json.loads(content)


# --- Эндпоинты ---
@app.get("/")
async def read_index():
    return FileResponse("static/index.html")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/version")
async def get_version():
    return {"version": APP_VERSION}


@app.get("/api/topics")
async def get_topics():
    """Возвращает список доступных тем (парсит md файл по заголовкам)"""
    syllabus = get_syllabus()
    topics = [line.strip("# ").strip() for line in syllabus.split("\n") if line.startswith("## ")]
    return {"topics": topics}


# Маршрут с параметром (требование PDF)
@app.get("/api/topics/{topic_name}")
async def get_topic_details(topic_name: str):
    syllabus = get_syllabus()
    if topic_name.lower() not in syllabus.lower():
        raise HTTPException(status_code=404, detail="Тема не найдена")
    return {"message": f"Тема '{topic_name}' найдена в базе знаний."}


@app.post("/api/generate")
async def generate_task(request: GenerateRequest):
    logger.info(f"Request to generate task. Topic: {request.topic}")
    syllabus = get_syllabus()

    # Если передана конкретная тема, фильтруем контекст
    context = syllabus
    if request.topic:
        lines = syllabus.split("\n")
        filtered = []
        capture = False
        for line in lines:
            if line.startswith("## ") and request.topic.lower() in line.lower():
                capture = True
            elif line.startswith("## ") and capture:
                break
            if capture:
                filtered.append(line)
        context = "\n".join(filtered)

    task_data = await generate_question_from_ai(context)
    return task_data
