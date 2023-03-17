import asyncio
from fastapi import Body, FastAPI, Depends
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import ChannelBase
from db import init_db, get_session
from userbot import run_telethon
from service import add_keywords, get_telegram_client, data_processing

#отключенная документация
# app = FastAPI(docs_url=None, redoc_url=None)
app = FastAPI()


@app.on_event("startup")
async def on_startup():
    client = await get_telegram_client()
    await init_db()
    asyncio.create_task(run_telethon(client))


@app.put("/listenchannel")
async def update_item(channel: ChannelBase = Body(embed=True),
                      session: AsyncSession = Depends(get_session)):
    row = await session.scalars(select(ChannelBase).
                                where(ChannelBase.link == channel.link))
    data = await add_keywords(row, channel)
    response = await data_processing(data, session)
    return response
