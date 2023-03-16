import os
import re
import asyncio
import dotenv
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from telethon.tl.functions.messages import ImportChatInviteRequest
import telethon.errors as e
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from models import ChannelBase


dotenv.load_dotenv()
dotenv_file = dotenv.find_dotenv()
api_id = os.environ.get("API_ID")
api_hash = os.environ.get("API_HASH")


async def delete_data(session: AsyncSession,
                      item: ChannelBase):
    await session.delete(item)
    await session.commit()


async def add_data(session: AsyncSession,
                   item: ChannelBase):
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


def set_env(key, value):
    os.environ[key] = value
    dotenv.set_key(dotenv_file, key, os.environ[key])
    return value


async def add_keywords(row, channel):
    data = row.first()
    if data:
        if len(channel.keywords) < 1:
            await leave_a_chat(data.link)
            return {'success': True, 'value': data, 'delete': True}
        data.keywords = channel.keywords
    else:
        result = await get_id_channel(link=channel.link)
        if result['success'] is True:
            data = ChannelBase(link=channel.link, keywords=channel.keywords,
                               channel_id=result['value'])
        else:
            return result
    return {'success': True, 'value': data, 'delete': False}


async def leave_a_chat(link):
    client: TelegramClient = await get_telegram_client()
    async with client:
        await client.delete_dialog(link)


async def get_id_channel(link):
    client = await get_telegram_client()
    async with client:
        try:
            if re.search(r'\+', link):
                hash_chat = re.sub(r'https://t.me/\+', '', link)
                update = await client(ImportChatInviteRequest(hash_chat.strip()))
            elif re.search(r'joinchat', link):
                hash_chat = re.sub('https://t.me/joinchat/', '', link)
                await client(ImportChatInviteRequest(hash_chat.strip()))
            else:
                update = await client(JoinChannelRequest(link))
        except e.UserAlreadyParticipantError:
            entity_channel = await client.get_entity(link)
            return {'success': True, 'value': entity_channel.id, 'delete': False}
        except Exception as error:
            print(error)
            return {'success': False, 'value': error, 'delete': False}
        else:
            channel_id = update.chats[0].id
            return {'success': True, 'value': channel_id, 'delete': False}


async def get_telegram_client():
    telethon_string = os.environ.get("TELETHON_STRING")
    if len(telethon_string) < 10:
        telethon_string = await set_telestring()
    return TelegramClient(
        StringSession(telethon_string),
        api_id=int(api_id),
        api_hash=api_hash
    )


async def set_telestring():
    async with TelegramClient(StringSession(), int(api_id), api_hash) as client:
        tele_string = client.session.save()
        set_env(key='TELETHON_STRING', value=tele_string.strip())
        return tele_string


async def data_processing(data: dict, session: AsyncSession):
    if data['success'] is True and data['delete'] is True:
        await delete_data(session, data['value'])
        return "Канал успешно удалён"
    if data['success'] is True:
        return await add_data(session, data['value'])
    else:
        text_error = str(data['value'])
        raise HTTPException(status_code=404, detail=text_error)
