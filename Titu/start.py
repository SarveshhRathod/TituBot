import os
import time
import asyncio 
import pyrogram
from pyrogram import Client, filters, enums
from pyrogram.errors import UserAlreadyParticipant, InviteHashExpired, UsernameNotOccupied
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message 
from config import API_ID, API_HASH, ERROR_MESSAGE, LOGIN_SYSTEM, CHANNEL_ID, WAITING_TIME, ADMINS
from database.db import db
from Titu.strings import HELP_TXT
from bot import TechVJUser

# Active user sessions cache in memory to speed up execution
USER_CLIENTS_CACHE = {}

class BatchTemp:
    IS_BATCH = {}

# Fast In-Memory Throttled Progress Bar (No Disk Write)
async def progress_bar(current, total, status_msg, action_type, last_update_time):
    now = time.time()
    if now - last_update_time[0] < 4 and current < total:
        return
    
    last_update_time[0] = now
    percentage = current * 100 / total
    speed = current / (now - last_update_time[1] + 0.001)
    
    progress_str = f"**{action_type}:** `{percentage:.1f}%`\n**Speed:** `{speed / 1024 / 1024:.2f} MB/s`"
    try:
        await status_msg.edit_text(progress_str)
    except Exception:
        pass

@Client.on_message(filters.command(["start"]))
async def send_start(client: Client, message: Message):
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
    
    buttons = [[
        InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/SarveshAsatkarr")
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)
    
    await message.reply_text(
        text=f"<b>👋 नमस्ते {message.from_user.mention},\n\nमैं Titu Bot हूँ। मैं Telegram की प्रतिबंधित (Restricted) सामग्री डाउनलोड कर सकता हूँ।\n\nशुरू करने के लिए /login करें या सहायता के लिए /help देखें।</b>", 
        reply_markup=reply_markup,
        quote=True
    )

@Client.on_message(filters.command(["help"]))
async def send_help(client: Client, message: Message):
    await message.reply_text(HELP_TXT, parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command(["stats"]) & filters.user(ADMINS))
async def show_stats(client: Client, message: Message):
    stats = await db.get_db_stats()
    stats_text = "\n".join(stats)
    await message.reply_text(f"<b>📊 Database Cluster Statistics:</b>\n\n{stats_text}")

@Client.on_message(filters.command(["cancel"]))
async def send_cancel(client: Client, message: Message):
    BatchTemp.IS_BATCH[message.from_user.id] = True
    await message.reply_text("<b>❌ आपका चल रहा कार्य सफलतापूर्वक रद्द कर दिया गया है।</b>")

@Client.on_message(filters.text & filters.private)
async def save(client: Client, message: Message):
    if ("https://t.me/+" in message.text or "https://t.me/joinchat/" in message.text) and not LOGIN_SYSTEM:
        if TechVJUser is None:
            return await message.reply_text("String Session सेट नहीं है।")
        try:
            await TechVJUser.join_chat(message.text)
            await message.reply_text("चैट सफलतापूर्वक जॉइन कर ली गई है।")
        except UserAlreadyParticipant:
            await message.reply_text("चैट पहले से जॉइन है।")
        except InviteHashExpired:
            await message.reply_text("अमान्य (Invalid) लिंक।")
        except Exception as e:
            await message.reply_text(f"Error: {e}")
        return

    if "https://t.me/" in message.text:
        if BatchTemp.IS_BATCH.get(message.from_user.id) == False:
            return await message.reply_text("<b>⚠️ आपका एक टास्क पहले से चल रहा है। कृपया प्रतीक्षा करें या /cancel का उपयोग करें।</b>")
        
        datas = message.text.split("/")
        temp = datas[-1].replace("?single", "").split("-")
        fromID = int(temp[0].strip())
        toID = int(temp[1].strip()) if len(temp) > 1 else fromID

        acc = None
        if LOGIN_SYSTEM:
            user_id = message.from_user.id
            if user_id in USER_CLIENTS_CACHE:
                acc = USER_CLIENTS_CACHE[user_id]
            else:
                user_data = await db.get_session(user_id)
                if not user_data:
                    return await message.reply_text("<b>प्रतिबंधित सामग्री डाउनलोड करने के लिए कृपया पहले /login करें।</b>")
                
                api_id = await db.get_api_id(user_id) or API_ID
                api_hash = await db.get_api_hash(user_id) or API_HASH
                try:
                    acc = Client(f"session_{user_id}", session_string=user_data, api_hash=api_hash, api_id=int(api_id))
                    await acc.connect()
                    USER_CLIENTS_CACHE[user_id] = acc
                except Exception:
                    return await message.reply_text("<b>आपका सेसन एक्सपायर हो गया है। कृपया फिर से /login करें।</b>")
        else:
            if TechVJUser is None:
                return await message.reply_text("String Session सेट नहीं है।")
            acc = TechVJUser

        BatchTemp.IS_BATCH[message.from_user.id] = False
        
        for msgid in range(fromID, toID + 1):
            if BatchTemp.IS_BATCH.get(message.from_user.id):
                break
            
            chatid = username = None
            if "https://t.me/c/" in message.text:
                chatid = int("-100" + datas[4])
            elif "https://t.me/b/" in message.text:
                username = datas[4]
            else:
                username = datas[3]

            target_chat = chatid if chatid else username
            try:
                await handle_private(client, acc, message, target_chat, msgid)
            except Exception as e:
                if ERROR_MESSAGE:
                    await message.reply_text(f"Error: {e}")

            await asyncio.sleep(WAITING_TIME)

        BatchTemp.IS_BATCH[message.from_user.id] = True

async def handle_private(client: Client, acc, message: Message, chatid, msgid: int):
    msg = await acc.get_messages(chatid, msgid)
    if not msg or msg.empty:
        return

    dest_chat = int(CHANNEL_ID) if CHANNEL_ID else message.chat.id
    
    if msg.text:
        return await client.send_message(dest_chat, msg.text, entities=msg.entities)

    smsg = await client.send_message(message.chat.id, "⚡ डाउनलोडिंग शुरू हो रही है...")
    start_time = time.time()
    last_update_time = [start_time, start_time]

    try:
        file_path = await acc.download_media(
            msg,
            progress=progress_bar,
            progress_args=[smsg, "Downloading", last_update_time]
        )
    except Exception as e:
        await smsg.delete()
        if ERROR_MESSAGE:
            await client.send_message(message.chat.id, f"Download Error: {e}")
        return

    if BatchTemp.IS_BATCH.get(message.from_user.id):
        if os.path.exists(file_path):
            os.remove(file_path)
        return

    last_update_time = [time.time(), time.time()]
    caption = msg.caption or ""

    try:
        if msg.document:
            await client.send_document(dest_chat, file_path, caption=caption, progress=progress_bar, progress_args=[smsg, "Uploading", last_update_time])
        elif msg.video:
            await client.send_video(dest_chat, file_path, caption=caption, progress=progress_bar, progress_args=[smsg, "Uploading", last_update_time])
        elif msg.audio:
            await client.send_audio(dest_chat, file_path, caption=caption, progress=progress_bar, progress_args=[smsg, "Uploading", last_update_time])
        elif msg.photo:
            await client.send_photo(dest_chat, file_path, caption=caption)
        elif msg.voice:
            await client.send_voice(dest_chat, file_path, caption=caption)
    except Exception as e:
        if ERROR_MESSAGE:
            await client.send_message(message.chat.id, f"Upload Error: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        await smsg.delete()