from fastapi import Body, FastAPI, Depends, HTTPException
from sqlmodel import select
from models import ChannelBase
from db import init_db, get_session
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import dotenv
import os
from userbot import run_main
from service import add_keywords, get_telegram_client

dotenv.load_dotenv()
dotenv_file = dotenv.find_dotenv()
admin_channel = os.environ.get('ADMIN_CHANNEL')
api_id = os.environ.get("API_ID")
api_hash = os.environ.get("API_HASH")

app = FastAPI()


def set_env(key, value):
    os.environ[key] = value
    dotenv.set_key(dotenv_file, key, os.environ[key])
    return value


async def delete_data(session, item):
    await session.delete(item)
    await session.commit()


async def add_data(session, item):
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@app.on_event("startup")
async def on_startup():
    client = await get_telegram_client()
    await init_db()
    asyncio.create_task(run_main(client))


@app.put("/listenchannel")
async def update_item(channel: ChannelBase = Body(embed=True), session: AsyncSession = Depends(get_session)):
    row = await session.scalars(select(ChannelBase).where(ChannelBase.link == channel.link))
    data = await add_keywords(row, channel)
    if data['success'] is True and data['delete'] is True:
        await delete_data(session, data['value'])
        return "Канал успешно удалён"
    if data['success'] is True:
        value = await add_data(session, data['value'])
        return value
    else:
        raise HTTPException(status_code=404, detail=data['value'])
