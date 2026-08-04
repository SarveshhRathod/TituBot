import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN, STRING_SESSION, LOGIN_SYSTEM

# Native Pending Requests Memory
PENDING_REQUESTS = {}

# Native ask_user helper function (Zero dependencies, Zero errors)
async def ask_user(bot: Client, chat_id: int, text: str, timeout: int = 600) -> Message:
    await bot.send_message(chat_id, text)
    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    PENDING_REQUESTS[chat_id] = fut
    try:
        response = await asyncio.wait_for(fut, timeout=timeout)
        return response
    except asyncio.TimeoutError:
        raise TimeoutError("समय समाप्त हो गया (Timeout)")
    finally:
        PENDING_REQUESTS.pop(chat_id, None)

if STRING_SESSION and not LOGIN_SYSTEM:
    TechVJUser = Client("TituUser", api_id=API_ID, api_hash=API_HASH, session_string=STRING_SESSION)
    TechVJUser.start()
else:
    TechVJUser = None

class Bot(Client):
    def __init__(self):
        super().__init__(
            "TituBot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins=dict(root="Titu"),
            workers=100,
            sleep_threshold=10
        )

    async def start(self):
        await super().start()
        print('✅ Titu Bot Successfully Started! Powered by @SarveshAsatkarr')

    async def stop(self, *args):
        await super().stop()
        print('🛑 Titu Bot Stopped.')

bot = Bot()

# High-priority message listener for OTP / Input prompts
@bot.on_message(filters.private, group=-100)
async def response_listener(client: Client, message: Message):
    chat_id = message.chat.id
    if chat_id in PENDING_REQUESTS:
        fut = PENDING_REQUESTS[chat_id]
        if not fut.done():
            fut.set_result(message)
            message.stop_propagation()

if __name__ == "__main__":
    bot.run()
