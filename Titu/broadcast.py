from pyrogram.errors import InputUserDeactivated, FloodWait, UserIsBlocked, PeerIdInvalid
from database.db import db
from pyrogram import Client, filters
from config import ADMINS
import asyncio
import time

async def broadcast_messages(user_id, message):
    try:
        await message.copy(chat_id=user_id)
        return True, "Success"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await broadcast_messages(user_id, message)
    except (InputUserDeactivated, UserIsBlocked, PeerIdInvalid):
        await db.delete_user(int(user_id))
        return False, "Deleted"
    except Exception:
        return False, "Error"

@Client.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def broadcast(bot, message):
    users = await db.get_all_users()
    b_msg = message.reply_to_message
    
    sts = await message.reply_text("<b>📢 ब्रॉडकास्ट शुरू हो रहा है...</b>")
    start_time = time.time()
    total_users = await db.total_users_count()
    done = success = failed = 0

    async for user in users:
        if 'id' in user:
            ok, _ = await broadcast_messages(int(user['id']), b_msg)
            if ok:
                success += 1
            else:
                failed += 1
            done += 1
            
            if done % 20 == 0:
                await sts.edit_text(f"<b>Broadcast Progress:\n\nTotal: {total_users}\nDone: {done}\nSuccess: {success}\nFailed: {failed}</b>")
    
    time_taken = round(time.time() - start_time, 2)
    await sts.edit_text(f"<b>✅ Broadcast Finished in {time_taken}s!\n\nTotal: {total_users}\nSuccess: {success}\nFailed: {failed}</b>")