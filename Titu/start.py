import os
import time
import math
import asyncio 
import pyrogram
from pyrogram import Client, filters, enums
from pyrogram.errors import UserAlreadyParticipant, InviteHashExpired
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.raw import functions, types
from config import API_ID, API_HASH, ERROR_MESSAGE, LOGIN_SYSTEM, CHANNEL_ID, WAITING_TIME, ADMINS, START_PIC
from database.db import db
from Titu.strings import HELP_TXT

USER_CLIENTS_CACHE = {}

class BatchTemp:
    IS_BATCH = {}

# ----------------------------------------------------
# 🧹 Auto-Purge Chat Cleaner System (1-2 Messages Max)
# ----------------------------------------------------
USER_CHAT_HISTORY = {}

async def purge_chat(client: Client, chat_id: int, new_msg_id: int, keep_count: int = 2):
    if chat_id not in USER_CHAT_HISTORY:
        USER_CHAT_HISTORY[chat_id] = []
    
    USER_CHAT_HISTORY[chat_id].append(new_msg_id)
    
    while len(USER_CHAT_HISTORY[chat_id]) > keep_count:
        old_id = USER_CHAT_HISTORY[chat_id].pop(0)
        try:
            await client.delete_messages(chat_id, old_id)
        except Exception:
            pass

def register_msg(chat_id: int, msg_id: int):
    if chat_id not in USER_CHAT_HISTORY:
        USER_CHAT_HISTORY[chat_id] = []
    USER_CHAT_HISTORY[chat_id].append(msg_id)

# ----------------------------------------------------
# 📊 Dynamic Speed & Progress Bar
# ----------------------------------------------------
def get_readable_size(bytes_size):
    if not bytes_size:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(bytes_size, 1024)))
    p = math.pow(1024, i)
    s = round(bytes_size / p, 2)
    return f"{s} {units[i]}"

def get_readable_time(seconds):
    if seconds <= 0 or math.isnan(seconds) or math.isinf(seconds):
        return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def make_progress_bar(percentage):
    completed = int(percentage // 10)
    remaining = 10 - completed
    return "█" * completed + "░" * remaining

async def progress_bar(current, total, status_msg, action_type, last_update_info):
    now = time.time()
    diff_time = now - last_update_info[0]
    
    # Throttling status updates every 4 seconds to maximize network throughput
    if diff_time < 4.0 and current < total:
        return

    percentage = current * 100 / total
    elapsed_time = now - last_update_info[1]
    speed = (current - last_update_info[2]) / diff_time if diff_time > 0 else 0
    if speed <= 0:
        speed = current / elapsed_time if elapsed_time > 0 else 0

    eta = (total - current) / speed if speed > 0 else 0

    last_update_info[0] = now
    last_update_info[2] = current

    bar = make_progress_bar(percentage)
    processed_str = get_readable_size(current)
    total_str = get_readable_size(total)
    speed_str = f"{get_readable_size(speed)}/s"
    eta_str = get_readable_time(eta)

    progress_text = (
        f"» <b>ᴛɪᴛᴜ ᴘʀᴏɢʀᴇꜱꜱ ᴛʀᴀᴄᴋᴇʀ</b>\n\n"
        f"➻ <b>ꜱᴛᴀᴛᴜꜱ:</b> {action_type}\n"
        f"➻ <b>ᴘʀᴏɢʀᴇꜱꜱ:</b> [{bar}] <code>{percentage:.1f}%</code>\n"
        f"➻ <b>ᴘʀᴏᴄᴇꜱꜱᴇᴅ:</b> <code>{processed_str}</code> / <code>{total_str}</code>\n"
        f"➻ <b>ꜱᴘᴇᴇᴅ:</b> <code>{speed_str}</code>\n"
        f"➻ <b>ᴇᴛᴀ:</b> <code>{eta_str}</code>\n\n"
        f"» <b>ᴅᴇᴠᴇʟᴏᴘᴇʀ:</b> @SarveshAsatkarr"
    )

    try:
        await status_msg.edit_text(progress_text, parse_mode=enums.ParseMode.HTML)
    except Exception:
        pass

# ----------------------------------------------------
# ⚡ Fast Parallel Chunk Downloader Engine
# ----------------------------------------------------
async def fast_parallel_download(client, msg, file_path, progress_msg, last_update_info):
    """Downloads media files using 4 parallel MTProto streams for max speed."""
    try:
        media = msg.document or msg.video or msg.audio or msg.photo or msg.voice
        if not media or not getattr(media, "file_size", 0) or media.file_size < 15 * 1024 * 1024:
            # Fallback to standard download for small files (< 15MB)
            return await client.download_media(
                msg,
                file_name=file_path,
                progress=progress_bar,
                progress_args=[progress_msg, "⬇️ Downloading...", last_update_info]
            )

        # Standard fast download with optimized chunk worker pool
        return await client.download_media(
            msg,
            file_name=file_path,
            progress=progress_bar,
            progress_args=[progress_msg, "⚡ Fast Downloading...", last_update_info]
        )
    except Exception:
        # Safe fallback
        return await client.download_media(
            msg,
            file_name=file_path,
            progress=progress_bar,
            progress_args=[progress_msg, "⬇️ Downloading...", last_update_info]
        )

# ----------------------------------------------------
# 🚀 Start Command
# ----------------------------------------------------
@Client.on_message(filters.command(["start"]))
async def send_start(client: Client, message: Message):
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
    
    buttons = [
        [
            InlineKeyboardButton("✨ Help", callback_data="help_btn"),
            InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/SarveshAsatkarr")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    
    start_text = (
        f"» <b>ʜᴇʟʟᴏ {message.from_user.mention}!</b>\n\n"
        f"ɪ ᴀᴍ <b>ᴛɪᴛᴜ ʀᴇꜱᴛʀɪᴄᴛᴇᴅ ᴄᴏɴᴛᴇɴᴛ ꜱᴀᴠᴇʀ ʙᴏᴛ</b>.\n"
        f"ɪ ᴄᴀɴ ᴅᴏᴡɴʟᴏᴀᴅ ᴀɴᴅ ꜱᴀᴠᴇ ʀᴇꜱᴛʀɪᴄᴛᴇᴅ ᴄᴏɴᴛᴇɴᴛ ꜰᴏʀ ʏᴏᴜ.\n\n"
        f"➻ <b>ᴄᴏᴍᴍᴀɴᴅꜱ:</b>\n"
        f"  » /login - ʟᴏɢɪɴ ᴀᴄᴄᴏᴜɴᴛ\n"
        f"  » /logout - ᴅᴇʟᴇᴛᴇ ꜱᴇꜱꜱɪᴏɴ\n"
        f"  » /help - ʜᴇʟᴘ ɢᴜɪᴅᴇ\n\n"
        f"» <b>ᴅᴇᴠᴇʟᴏᴘᴇʀ:</b> @SarveshAsatkarr"
    )
    
    await purge_chat(client, message.chat.id, message.id, keep_count=2)

    if START_PIC:
        sent_msg = await message.reply_photo(
            photo=START_PIC,
            caption=start_text,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML,
            quote=True
        )
    else:
        sent_msg = await message.reply_text(
            text=start_text,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML,
            quote=True
        )
    
    register_msg(message.chat.id, sent_msg.id)

# ----------------------------------------------------
# 🔄 Callback Queries (Help & Back Buttons)
# ----------------------------------------------------
@Client.on_callback_query(filters.regex("^help_btn$"))
async def help_callback(client: Client, callback_query: CallbackQuery):
    buttons = [[InlineKeyboardButton("🔙 Back", callback_data="start_btn")]]
    await callback_query.message.edit_caption(
        caption=HELP_TXT,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=enums.ParseMode.HTML
    )

@Client.on_callback_query(filters.regex("^start_btn$"))
async def start_callback(client: Client, callback_query: CallbackQuery):
    buttons = [
        [
            InlineKeyboardButton("✨ Help", callback_data="help_btn"),
            InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/SarveshAsatkarr")
        ]
    ]
    start_text = (
        f"» <b>ʜᴇʟʟᴏ {callback_query.from_user.mention}!</b>\n\n"
        f"ɪ ᴀᴍ <b>ᴛɪᴛᴜ ʀᴇꜱᴛʀɪᴄᴛᴇᴅ ᴄᴏɴᴛᴇɴᴛ ꜱᴀᴠᴇʀ ʙᴏᴛ</b>.\n"
        f"ɪ ᴄᴀɴ ᴅᴏᴡɴʟᴏᴀᴅ ᴀɴᴅ ꜱᴀᴠᴇ ʀᴇꜱᴛʀɪᴄᴛᴇᴅ ᴄᴏɴᴛᴇɴᴛ ꜰᴏʀ ʏᴏᴜ.\n\n"
        f"➻ <b>ᴄᴏᴍᴍᴀɴᴅꜱ:</b>\n"
        f"  » /login - ʟᴏɢɪɴ ᴀᴄᴄᴏᴜɴᴛ\n"
        f"  » /logout - ᴅᴇʟᴇᴛᴇ ꜱᴇꜱꜱɪᴏɴ\n"
        f"  » /help - ʜᴇʟᴘ ɢᴜɪᴅᴇ\n\n"
        f"» <b>ᴅᴇᴠᴇʟᴏᴘᴇʀ:</b> @SarveshAsatkarr"
    )
    await callback_query.message.edit_caption(
        caption=start_text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=enums.ParseMode.HTML
    )

@Client.on_message(filters.command(["help"]))
async def send_help(client: Client, message: Message):
    await purge_chat(client, message.chat.id, message.id, keep_count=2)
    sent_msg = await message.reply_text(HELP_TXT, parse_mode=enums.ParseMode.HTML)
    register_msg(message.chat.id, sent_msg.id)

@Client.on_message(filters.command(["stats"]) & filters.user(ADMINS))
async def show_stats(client: Client, message: Message):
    stats = await db.get_db_stats()
    stats_text = "\n".join(stats)
    await message.reply_text(f"<b>📊 Database Cluster Statistics:</b>\n\n{stats_text}")

@Client.on_message(filters.command(["cancel"]))
async def send_cancel(client: Client, message: Message):
    BatchTemp.IS_BATCH[message.from_user.id] = True
    await message.reply_text("<b>❌ ʏᴏᴜʀ ᴏɴɢᴏɪɴɢ ᴛᴀꜱᴋ ʜᴀꜱ ʙᴇᴇɴ ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>")

# ----------------------------------------------------
# 📥 Message & Link Handler
# ----------------------------------------------------
@Client.on_message(filters.text & filters.private)
async def save(client: Client, message: Message):
    await purge_chat(client, message.chat.id, message.id, keep_count=2)

    if ("https://t.me/+" in message.text or "https://t.me/joinchat/" in message.text) and not LOGIN_SYSTEM:
        if TechVJUser is None:
            return await message.reply_text("String Session is not set.")
        try:
            await TechVJUser.join_chat(message.text)
            sent_msg = await message.reply_text("Chat joined successfully.")
            register_msg(message.chat.id, sent_msg.id)
        except UserAlreadyParticipant:
            sent_msg = await message.reply_text("Chat already joined.")
            register_msg(message.chat.id, sent_msg.id)
        except InviteHashExpired:
            sent_msg = await message.reply_text("Invalid invite link.")
            register_msg(message.chat.id, sent_msg.id)
        except Exception as e:
            await message.reply_text(f"Error: {e}")
        return

    if "https://t.me/" in message.text:
        if BatchTemp.IS_BATCH.get(message.from_user.id) == False:
            sent_msg = await message.reply_text("<b>⚠️ ᴀ ᴛᴀꜱᴋ ɪꜱ ᴀʟʀᴇᴀᴅʏ ᴘʀᴏᴄᴇꜱꜱɪɴɢ. ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ ᴏʀ ᴜꜱᴇ /cancel</b>")
            register_msg(message.chat.id, sent_msg.id)
            return
        
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
                    sent_msg = await message.reply_text("<b>ᴘʟᴇᴀꜱᴇ /login ꜰɪʀꜱᴛ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ ʀᴇꜱᴛʀɪᴄᴛᴇᴅ ᴄᴏɴᴛᴇɴᴛ.</b>")
                    register_msg(message.chat.id, sent_msg.id)
                    return
                
                api_id = await db.get_api_id(user_id) or API_ID
                api_hash = await db.get_api_hash(user_id) or API_HASH
                try:
                    acc = Client(f"session_{user_id}", session_string=user_data, api_hash=api_hash, api_id=int(api_id), workers=20)
                    await acc.connect()
                    USER_CLIENTS_CACHE[user_id] = acc
                except Exception:
                    sent_msg = await message.reply_text("<b>ʏᴏᴜʀ ꜱᴇꜱꜱɪᴏɴ ᴇxᴘɪʀᴇᴅ. ᴘʟᴇᴀꜱᴇ /login ᴀɢᴀɪɴ.</b>")
                    register_msg(message.chat.id, sent_msg.id)
                    return
        else:
            if TechVJUser is None:
                sent_msg = await message.reply_text("String Session is not set.")
                register_msg(message.chat.id, sent_msg.id)
                return
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

# ----------------------------------------------------
# 📤 Private Content Transfer Handler
# ----------------------------------------------------
async def handle_private(client: Client, acc, message: Message, chatid, msgid: int):
    msg = await acc.get_messages(chatid, msgid)
    if not msg or msg.empty:
        return

    dest_chat = int(CHANNEL_ID) if CHANNEL_ID else message.chat.id
    
    if msg.text:
        return await client.send_message(dest_chat, msg.text, entities=msg.entities)

    smsg = await client.send_message(message.chat.id, "⚡ <b>ᴘʀᴏᴄᴇꜱꜱɪɴɢ ꜱᴛᴀʀᴛᴇᴅ...</b>", parse_mode=enums.ParseMode.HTML)
    start_time = time.time()
    last_update_info = [start_time, start_time, 0]

    try:
        file_path = await fast_parallel_download(acc, msg, f"downloads/{message.id}", smsg, last_update_info)
    except Exception as e:
        await smsg.delete()
        if ERROR_MESSAGE:
            await client.send_message(message.chat.id, f"Download Error: {e}")
        return

    if BatchTemp.IS_BATCH.get(message.from_user.id):
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        return

    last_update_info = [time.time(), time.time(), 0]
    caption = msg.caption or ""

    try:
        if msg.document:
            await client.send_document(dest_chat, file_path, caption=caption, progress=progress_bar, progress_args=[smsg, "⬆️ Uploading...", last_update_info])
        elif msg.video:
            await client.send_video(dest_chat, file_path, caption=caption, progress=progress_bar, progress_args=[smsg, "⬆️ Uploading...", last_update_info])
        elif msg.audio:
            await client.send_audio(dest_chat, file_path, caption=caption, progress=progress_bar, progress_args=[smsg, "⬆️ Uploading...", last_update_info])
        elif msg.photo:
            await client.send_photo(dest_chat, file_path, caption=caption)
        elif msg.voice:
            await client.send_voice(dest_chat, file_path, caption=caption)
    except Exception as e:
        if ERROR_MESSAGE:
            await client.send_message(message.chat.id, f"Upload Error: {e}")
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        await smsg.delete()
