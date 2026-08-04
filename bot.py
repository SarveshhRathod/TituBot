from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN, STRING_SESSION, LOGIN_SYSTEM

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
        self.pending_requests = {}

    async def start(self):
        await super().start()
        print('✅ Titu Bot Successfully Started! Powered by @SarveshAsatkarr')

    async def stop(self, *args):
        await super().stop()
        print('🛑 Titu Bot Stopped.')

if __name__ == "__main__":
    bot = Bot()
    bot.run()
