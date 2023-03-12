from telethon.tl.functions.messages import ImportChatInviteRequest
from models import ChannelBase
import dotenv
import telethon.errors as e
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
import os
import re

dotenv.load_dotenv()
dotenv_file = dotenv.find_dotenv()
api_id = os.environ.get("API_ID")
api_hash = os.environ.get("API_HASH")


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
            data = ChannelBase(link=channel.link, keywords=channel.keywords, channel_id=result['value'])
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
                entity_channel = await client(ImportChatInviteRequest(hash_chat.strip()))
            else:
                entity_channel = await client(JoinChannelRequest(link))
        except e.UserAlreadyParticipantError:
            entity_channel = await client.get_entity(link)
            return {'success': True, 'value': entity_channel.id, 'delete': False}
        except (ValueError, e.ChannelInvalidError,
                e.ChannelPrivateError,
                e.InviteRequestSentError,
                e.ChannelsTooMuchError) as error:
            print(error)
            return {'success': False, 'value': error, 'delete': False}
        else:
            channel_id = entity_channel.chats[0].id
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
