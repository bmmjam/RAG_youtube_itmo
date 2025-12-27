import asyncio
import logging
import os
import re
from logging.handlers import RotatingFileHandler

import httpx
import openai
from aiogram import Bot
from aiogram import Dispatcher
from aiogram import executor
from aiogram import types
from custom_embedding import OpenAIEmbeddingProxy
from dotenv import load_dotenv
from llama_index import ServiceContext
from llama_index import StorageContext
from llama_index import load_index_from_storage
from openai import AsyncOpenAI


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(module)s: %(message)s",
    handlers=[
        RotatingFileHandler("app/logs/app.log", maxBytes=5_000_000, backupCount=2),
        logging.StreamHandler(),
    ],
)

load_dotenv()

TOKEN = os.getenv("TG_TOKEN")
BOT_ID_ = os.getenv("BOT_ID")
BOT_ID = int(BOT_ID_) if BOT_ID_ else None
PROXY = os.getenv("PROXY")

MODEL_NAME = "gpt-4o-mini"

logging.info("Initialization has started")

http_client = httpx.AsyncClient(proxies=PROXY)
client = AsyncOpenAI(http_client=http_client)

embed_model = OpenAIEmbeddingProxy(http_client=http_client)
service_context = ServiceContext.from_defaults(embed_model=embed_model)

storage_context = StorageContext.from_defaults(persist_dir="data/index_storage_1024")

index = load_index_from_storage(
    storage_context,
    service_context=service_context,
)

query_engine = index.as_query_engine(
    similarity_top_k=3,
    response_mode="no_text",
    include_text=True,
)


logging.info("Initialization is complete")


bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

message_queue: asyncio.Queue[tuple[int, str]] = asyncio.Queue()

retrival_query_regex = re.compile(r"Вопрос: (.*?)\n\n", re.DOTALL)
message_regex = re.compile(r'@rag_youtube_itmo_bot[,\s]*')


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


async def message_worker() -> None:
    while True:
        chat_id, text = await message_queue.get()
        await bot.send_message(chat_id, text, parse_mode="HTML")
        await asyncio.sleep(6)


async def on_startup(_: Dispatcher) -> None:
    asyncio.create_task(message_worker())


async def keep_typing(chat_id: int, interval: int = 5) -> None:
    while True:
        await bot.send_chat_action(chat_id, "typing")
        await asyncio.sleep(interval)


# -------------------- core logic --------------------


async def llm_context_judge(context: str, question: str) -> bool:
    """
    LLM-судья: отвечает, содержит ли контекст
    ДОСТАТОЧНУЮ информацию для ответа на вопрос.
    """
    prompt = f"""
Контекст:
---
{context}
---

Вопрос:
{question}

Достаточно ли информации в контексте, чтобы ответить на вопрос
ФАКТИЧЕСКИ и КОНКРЕТНО, без домыслов?

Ответь строго одним словом: YES или NO.
"""
    resp = await client.chat.completions.create(
        model=MODEL_NAME,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip() == "YES"


async def answer(user_message: str, reply_to_message: str | None = None) -> str:
    # ---------- retrieval ----------
    if reply_to_message:
        retrival_query = retrival_query_regex.findall(reply_to_message)[0] + user_message
    else:
        retrival_query = user_message

    retrival = await query_engine.aquery(retrival_query)

    source_nodes = retrival.source_nodes

    for i, node in enumerate(source_nodes, 1):
        logging.info("%s node: %s", i, node.text)

    if not source_nodes:
        return (
            f"<b>Вопрос:</b> <i>{escape_html(user_message)}</i>\n\n"
            f"<b>Ответ:</b> В базе знаний нет информации по этому вопросу."
        )

    context_text = " ".join(node.text for node in source_nodes)
    context_text = escape_html(context_text)

    # ---------- LLM judge ----------
    is_relevant = await llm_context_judge(context_text, user_message)
    logging.info("Context judge: %s", is_relevant)

    if not is_relevant:
        return (
            f"<b>Вопрос:</b> <i>{escape_html(user_message)}</i>\n\n"
            f"<b>Ответ:</b> В базе знаний нет релевантной информации для ответа на этот вопрос."
        )

    # ---------- generation ----------
    generation_prompt = f"""
Используя информацию ниже, ответь на вопрос пользователя.
Если информации недостаточно — явно укажи это.

Контекст:
---
{context_text}
---

Вопрос:
{user_message}
"""

    gpt_response = await client.chat.completions.create(
        model=MODEL_NAME,
        temperature=0,
        messages=[{"role": "user", "content": generation_prompt}],
    )

    main_answer = gpt_response.choices[0].message.content

    urls = {
        f'&#x25CF; <a href="{n.metadata["url"]}">{escape_html(n.metadata["title"])}</a>'
        for n in source_nodes
        if "url" in n.metadata and "title" in n.metadata
    }

    extended = ""
    if urls:
        extended = "\n\n<b>Источники:</b>\n" + "\n".join(urls)

    return f"<b>Вопрос:</b> <i>{escape_html(user_message)}</i>\n\n" f"<b>Ответ:</b> {main_answer}" f"{extended}"


@dp.message_handler(commands=["start", "help"])
async def send_welcome(message: types.Message) -> None:
    greeting = "Привет, я RAG-бот по YouTube-контенту.\n" "Задавай вопросы, тегнув меня: @rag_youtube_itmo_bot"
    await message_queue.put((message.chat.id, greeting))


@dp.message_handler(lambda m: "@rag_youtube_itmo_bot" in m.text)
async def handle_tag(message: types.Message) -> None:
    logging.info("Message accepted: %s", message.text)
    typing_task = asyncio.create_task(keep_typing(message.chat.id))
    try:
        user_message = message_regex.sub("", message.text)
        try:
            response = await answer(user_message)
        except openai.APITimeoutError:
            response = "Сервис временно недоступен."
    finally:
        typing_task.cancel()

    await message_queue.put((message.chat.id, response))


@dp.message_handler(lambda m: m.reply_to_message and m.reply_to_message.from_user.id == BOT_ID)
async def handle_reply(message: types.Message) -> None:
    logging.info("Reply accepted: %s", message.text)
    typing_task = asyncio.create_task(keep_typing(message.chat.id))
    try:
        original = message.reply_to_message.text
        try:
            response = await answer(message.text, reply_to_message=original)
        except openai.APITimeoutError:
            response = "Сервис временно недоступен."
    finally:
        typing_task.cancel()

    await message_queue.put((message.chat.id, response))


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
