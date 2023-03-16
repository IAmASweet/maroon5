import asyncio
import datetime
import os
import re
from typing import Union

import dotenv
from rapidfuzz import fuzz, process
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import select
from telethon import events
from telethon.client.telegramclient import TelegramClient
from telethon.errors.rpcerrorlist import MessageIdInvalidError, \
    QuizAnswerMissingError, \
    TopicDeletedError, TimeoutError, \
    BroadcastPublicVotersForbiddenError, FloodWaitError
from telethon.events import Album, NewMessage, MessageEdited
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.types import Channel, Chat, User

from db import engine
from models import ChannelBase

dotenv.load_dotenv()
admin_channel = os.environ.get('ADMIN_CHANNEL')
api_id = os.environ.get("API_ID")
api_hash = os.environ.get("API_HASH")


async def forward_message(chat: Union[Channel, Chat], message: str,
                          event: Union[Album, NewMessage, MessageEdited],
                          sender: Union[Channel, Chat, User],
                          client: TelegramClient) -> None:
    url, keywords = await check_channels(chat.id)
    if keywords and message:
        result = check_keywords_in_message(message, keywords)
        if result:
            text = await create_text(sender, event, message, url, chat)
            await send_message_to_channel(event, client, text)


async def send_message_to_channel(event: Union[Album, NewMessage, MessageEdited],
                                  client: TelegramClient, text: str) -> None:
    try:
        if isinstance(event, events.messageedited.MessageEdited.Event):
            if event.message.grouped_id is not None:
                await send_album_message(event.message.media, client, text)
            else:
                await client.send_message(admin_channel, text)
        elif isinstance(event, events.newmessage.NewMessage.Event):
            if event.message.media:
                await client.send_message(admin_channel, text, file=event.message.media)
            else:
                await client.send_message(admin_channel, text)
        else:
            await send_album_message(event.messages, client, text)
    except (MessageIdInvalidError,
            QuizAnswerMissingError,
            TopicDeletedError,
            TimeoutError,
            BroadcastPublicVotersForbiddenError) as error:
        print(error)
        pass


async def send_album_message(file: list, client: TelegramClient,
                             text: str) -> None:
    await client.send_message(
        admin_channel,
        file=file,
        message=text,
    )


async def create_text(sender: Union[Channel, Chat, User], event: events,
                      message: str, url: str, chat: Union[Channel, Chat]) -> str:
    username_text = ''
    link_user = f'tg://user?id={sender.id}'
    message_id: int
    date_msg: datetime.datetime
    message_id, date_msg = await get_msg_id_and_date(event)
    if sender.username:
        username_text = 'Username отправителя: ' + '@' + sender.username
    text = f"Название канала: {chat.title}\n" \
           f"Ссылка на чат: {url}\n" \
           f"Текст сообщения: {message}\n" \
           f"Ссылка на сообщение: https://t.me/c/{chat.id}/{message_id}\n" \
           f"Ссылка на пользователя: {link_user}\n" \
           f"ID сообщения: {message_id}\n" \
           f"Время: {date_msg}\n" \
           f"{username_text if sender.username else ''}\n"
    return text


async def get_msg_id_and_date(event: events):
    if isinstance(event, events.album.Album.Event):
        message_id = event.original_update.message.id
        date_msg = event.original_update.message.date
    elif isinstance(event, events.messageedited.MessageEdited.Event) \
            or isinstance(event, events.newmessage.NewMessage.Event):
        message_id = event.message.id
        date_msg = event.date
    return message_id, date_msg


def check_keywords_in_message(message: str, keywords: list) -> bool:
    the_fuzz = eval(os.environ.get('THEFUZZ'))
    if the_fuzz:
        return check_the_fuzz(message, keywords)
    for phrase in keywords:
        message = re.sub('[^\x00-\x7Fа-яА-Я]', "", message)
        if phrase.lower() in message.lower():
            return True
    return False


def check_the_fuzz(message: str, keywords: list) -> bool:
    the_fuzz_points = int(os.environ.get('THEFUZZ_POINTS'))
    list_of_keywords = process.extract(message, keywords, scorer=fuzz.token_set_ratio)
    checked_words = [item for item in list_of_keywords if item[1] > the_fuzz_points]
    return True if len(checked_words) > 0 else False


async def check_channels(chat_id: int) -> list:
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        rows = await session.scalars(select(ChannelBase).where(ChannelBase.channel_id == chat_id))
        channel = rows.first()
        if channel:
            return [channel.link, channel.keywords]
        return [None, None]


async def run_telethon(client):
    await client.start()
    try:
        if re.search(r'joinchat', admin_channel):
            hash_chat = re.sub('https://t.me/joinchat/', '', admin_channel)
            await client(ImportChatInviteRequest(hash_chat.strip()))
        elif re.search(r'\+', admin_channel):
            hash_chat = re.sub(r'https://t.me/\+', '', admin_channel)
            await client(ImportChatInviteRequest(hash_chat.strip()))
        else:
            await client(JoinChannelRequest(admin_channel))
    except FloodWaitError as error:
        print(error)
        await asyncio.sleep(error.seconds)
    except Exception as error:
        print(error)
        pass

    @client.on(Album)
    async def album_handler(event: Album):
        sender = await event.get_sender()
        chat = await event.get_chat()
        msg = event.text
        try:
            if isinstance(chat, Channel) or isinstance(chat, Chat):
                await forward_message(chat=chat, message=msg,
                                      event=event, sender=sender, client=client)
        except Exception as e:
            print(e)
            pass

    @client.on(NewMessage)
    async def new_msg_handler(event: NewMessage):
        sender = await event.get_sender()
        chat = await event.get_chat()
        msg = event.raw_text
        try:
            if isinstance(chat, Channel) or isinstance(chat, Chat):
                if event.message.grouped_id is None:
                    await forward_message(chat=chat, message=msg,
                                          event=event, sender=sender, client=client)
        except Exception as e:
            print(e)
            pass

    @client.on(MessageEdited)
    async def handler(event: MessageEdited):
        sender = await event.get_sender()
        chat = await event.get_chat()
        msg = event.raw_text
        try:
            if isinstance(chat, Channel) or isinstance(chat, Chat):
                await forward_message(chat=chat, message=msg,
                                      event=event, sender=sender, client=client)
        except Exception as e:
            print(e)
            pass

    await client.run_until_disconnected()
