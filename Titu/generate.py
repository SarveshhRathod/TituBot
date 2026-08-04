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
from bot import ask_user

@Client.on_message(filters.private & filters.command(["logout"]))
async def logout(client, message):
    user_id = message.from_user.id
    user_data = await db.get_session(user_id)  
    if user_data is None:
        return await message.reply_text("<b>आप लॉग इन नहीं हैं!</b>")
        
    await db.set_session(user_id, session=None)
    if user_id in USER_CLIENTS_CACHE:
        try:
            await USER_CLIENTS_CACHE[user_id].disconnect()
        except Exception:
            pass
        del USER_CLIENTS_CACHE[user_id]
        
    await message.reply_text("<b>सफलतापूर्वक Logout हो गया! 🔒</b>")

@Client.on_message(filters.private & filters.command(["login"]))
async def login(bot: Client, message: Message):
    user_id = message.from_user.id
    user_data = await db.get_session(user_id)
    if user_data is not None:
        return await message.reply_text("<b>आप पहले से Logged In हैं। नया सेसन जोड़ने के लिए /logout करें।</b>")
    
    try:
        api_id_msg = await ask_user(bot, user_id, "<b>अपना API ID भेजें:\n\nयदि आप डिफॉल्ट उपयोग करना चाहते हैं तो /skip टाइप करें।</b>")
        if api_id_msg.text == "/skip":
            api_id = API_ID
            api_hash = API_HASH
        else:
            try:
                api_id = int(api_id_msg.text)
            except ValueError:
                return await api_id_msg.reply("API ID अंक (Number) में होना चाहिए। फिर से /login करें।")
                
            api_hash_msg = await ask_user(bot, user_id, "<b>अब अपना API HASH भेजें:</b>")
            api_hash = api_hash_msg.text
            
        phone_number_msg = await ask_user(bot, user_id, "<b>अपना फोन नंबर कंट्री कोड के साथ भेजें (जैसे: +919876543210):</b>")
        if phone_number_msg.text == '/cancel':
            return await phone_number_msg.reply('प्रक्रिया रद्द कर दी गई!')
            
        phone_number = phone_number_msg.text
        temp_client = Client(":memory:", api_id=api_id, api_hash=api_hash)
        await temp_client.connect()
        
        try:
            code = await temp_client.send_code(phone_number)
            phone_code_msg = await ask_user(
                bot, 
                user_id, 
                "<b>Telegram OTP दर्ज करें।\n\nयदि आपका OTP `12345` है, तो इसे स्पेस देकर भेजें: `1 2 3 4 5`</b>", 
                timeout=600
            )
        except PhoneNumberInvalid:
            await temp_client.disconnect()
            return await phone_number_msg.reply('अमान्य फोन नंबर!')

        if phone_code_msg.text == '/cancel':
            await temp_client.disconnect()
            return await phone_code_msg.reply('प्रक्रिया रद्द!')

        try:
            phone_code = phone_code_msg.text.replace(" ", "")
            await temp_client.sign_in(phone_number, code.phone_code_hash, phone_code)
        except PhoneCodeInvalid:
            await temp_client.disconnect()
            return await phone_code_msg.reply('अमान्य OTP!')
        except PhoneCodeExpired:
            await temp_client.disconnect()
            return await phone_code_msg.reply('OTP समय समाप्त!')
        except SessionPasswordNeeded:
            two_step_msg = await ask_user(bot, user_id, '<b>Two-Step Verification पासवर्ड दर्ज करें:</b>', timeout=300)
            if two_step_msg.text == '/cancel':
                await temp_client.disconnect()
                return await two_step_msg.reply('प्रक्रिया रद्द!')
            try:
                await temp_client.check_password(password=two_step_msg.text)
            except PasswordHashInvalid:
                await temp_client.disconnect()
                return await two_step_msg.reply('गलत पासवर्ड!')

        string_session = await temp_client.export_session_string()
        await temp_client.disconnect()
        
        await db.set_session(user_id, session=string_session)
        await db.set_api_credentials(user_id, api_id, api_hash)
        
        await bot.send_message(user_id, "<b>🎉 आपका अकाउंट सफलतापूर्वक Login हो गया है!</b>")
    except TimeoutError:
        await bot.send_message(user_id, "<b>❌ समय समाप्त हो गया। कृपया दोबारा /login करें।</b>")
    except Exception as e:
        await bot.send_message(user_id, f"<b>एरर: {e}</b>")
