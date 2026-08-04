import asyncio
from pyrogram.types import Message
from pyrogram import Client, filters
from pyrogram.errors import (
    PhoneNumberInvalid,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    SessionPasswordNeeded,
    PasswordHashInvalid
)
from config import API_ID, API_HASH
from database.db import db
from Titu.start import USER_CLIENTS_CACHE

# ----------------------------------------------------
# 🎯 Custom Built-In Ask Helper System
# ----------------------------------------------------
async def ask_user(client: Client, chat_id: int, text: str, timeout: int = 600) -> Message:
    if not hasattr(client, "pending_requests"):
        client.pending_requests = {}
        
    await client.send_message(chat_id, text)
    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    client.pending_requests[chat_id] = fut
    try:
        response = await asyncio.wait_for(fut, timeout=timeout)
        return response
    except asyncio.TimeoutError:
        raise TimeoutError("Timeout")
    finally:
        client.pending_requests.pop(chat_id, None)

# High-priority global listener for incoming OTP / prompt replies
@Client.on_message(filters.private, group=-100)
async def global_ask_listener(client: Client, message: Message):
    if hasattr(client, "pending_requests") and message.chat.id in client.pending_requests:
        fut = client.pending_requests[message.chat.id]
        if not fut.done():
            fut.set_result(message)
            message.stop_propagation()

# ----------------------------------------------------
# 🔒 Logout Command
# ----------------------------------------------------
@Client.on_message(filters.private & filters.command(["logout"]))
async def logout(client: Client, message: Message):
    user_id = message.from_user.id
    user_data = await db.get_session(user_id)  
    if user_data is None:
        return await message.reply_text("<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ʟᴏɢɢᴇᴅ ɪɴ!</b>")
        
    await db.set_session(user_id, session=None)
    if user_id in USER_CLIENTS_CACHE:
        try:
            await USER_CLIENTS_CACHE[user_id].disconnect()
        except Exception:
            pass
        del USER_CLIENTS_CACHE[user_id]
        
    await message.reply_text("<b>ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ʟᴏɢɢᴇᴅ ᴏᴜᴛ! 🔒</b>")

# ----------------------------------------------------
# 🔑 Login Command
# ----------------------------------------------------
@Client.on_message(filters.private & filters.command(["login"]))
async def login(bot: Client, message: Message):
    user_id = message.from_user.id
    user_data = await db.get_session(user_id)
    if user_data is not None:
        return await message.reply_text("<b>ʏᴏᴜ ᴀʀᴇ ᴀʟʀᴇᴀᴅʏ ʟᴏɢɢᴇᴅ ɪɴ. ᴜꜱᴇ /logout ꜰɪʀꜱᴛ.</b>")
    
    try:
        # Step 1: Ask API ID
        api_id_msg = await ask_user(bot, user_id, "<b>ꜱᴇɴᴅ ʏᴏᴜʀ API ID:\n\nꜱᴇɴᴅ /skip ᴛᴏ ᴜꜱᴇ ᴅᴇꜰᴀᴜʟᴛ.</b>")
        if api_id_msg.text == "/skip":
            api_id = API_ID
            api_hash = API_HASH
        else:
            try:
                api_id = int(api_id_msg.text)
            except ValueError:
                return await api_id_msg.reply("API ID must be an integer. Try /login again.")
                
            # Step 2: Ask API HASH
            api_hash_msg = await ask_user(bot, user_id, "<b>ɴᴏᴡ ꜱᴇɴᴅ ʏᴏᴜʀ API HASH:</b>")
            api_hash = api_hash_msg.text
            
        # Step 3: Ask Phone Number
        phone_number_msg = await ask_user(bot, user_id, "<b>ꜱᴇɴᴅ ʏᴏᴜʀ ᴘʜᴏɴᴇ ɴᴜᴍʙᴇʀ ᴡɪᴛʜ ᴄᴏᴜɴᴛʀʏ ᴄᴏᴅᴇ (ᴇ.ɢ. +1234567890):</b>")
        if phone_number_msg.text == '/cancel':
            return await phone_number_msg.reply('Process cancelled!')
            
        phone_number = phone_number_msg.text
        temp_client = Client(":memory:", api_id=api_id, api_hash=api_hash)
        await temp_client.connect()
        
        try:
            # Step 4: Send & Ask OTP
            code = await temp_client.send_code(phone_number)
            phone_code_msg = await ask_user(
                bot, 
                user_id, 
                "<b>ᴇɴᴛᴇʀ Telegram OTP.\n\nɪꜰ OTP ɪꜱ <code>12345</code>, ꜱᴇɴᴅ ɪᴛ ᴀꜱ: <code>1 2 3 4 5</code></b>", 
                timeout=600
            )
        except PhoneNumberInvalid:
            await temp_client.disconnect()
            return await phone_number_msg.reply('Invalid phone number!')

        if phone_code_msg.text == '/cancel':
            await temp_client.disconnect()
            return await phone_code_msg.reply('Process cancelled!')

        try:
            phone_code = phone_code_msg.text.replace(" ", "")
            await temp_client.sign_in(phone_number, code.phone_code_hash, phone_code)
        except PhoneCodeInvalid:
            await temp_client.disconnect()
            return await phone_code_msg.reply('Invalid OTP!')
        except PhoneCodeExpired:
            await temp_client.disconnect()
            return await phone_code_msg.reply('OTP expired!')
        except SessionPasswordNeeded:
            # Step 5: Ask Two-Step Password
            two_step_msg = await ask_user(bot, user_id, '<b>ᴇɴᴛᴇʀ ʏᴏᴜʀ ᴛᴡᴏ-ꜱᴛᴇᴘ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴘᴀꜱꜱᴡᴏʀᴅ:</b>', timeout=300)
            if two_step_msg.text == '/cancel':
                await temp_client.disconnect()
                return await two_step_msg.reply('Process cancelled!')
            try:
                await temp_client.check_password(password=two_step_msg.text)
            except PasswordHashInvalid:
                await temp_client.disconnect()
                return await two_step_msg.reply('Invalid password!')

        string_session = await temp_client.export_session_string()
        await temp_client.disconnect()
        
        await db.set_session(user_id, session=string_session)
        await db.set_api_credentials(user_id, api_id, api_hash)
        
        await bot.send_message(user_id, "<b>🎉 ᴀᴄᴄᴏᴜɴᴛ ʟᴏɢɢᴇᴅ ɪɴ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ!</b>")
    except TimeoutError:
        await bot.send_message(user_id, "<b>❌ ᴛɪᴍᴇᴏᴜᴛ. ᴘʟᴇᴀꜱᴇ ᴛʀʏ /login ᴀɢᴀɪɴ.</b>")
    except Exception as e:
        await bot.send_message(user_id, f"<b>Error: {e}</b>")
