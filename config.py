import os

# Login feature configuration
LOGIN_SYSTEM = bool(os.environ.get('LOGIN_SYSTEM', True))

if not LOGIN_SYSTEM:
    STRING_SESSION = os.environ.get("STRING_SESSION", "")
else:
    STRING_SESSION = None

# Telegram API Credentials
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")

# Admin configuration (Space or comma separated for multiple admins)
ADMINS = [int(admin) for admin in os.environ.get("ADMINS", "6073523936").split()]

# Upload Channel ID (Optional)
CHANNEL_ID = os.environ.get("CHANNEL_ID", "")

# Multiple MongoDB URIs (Comma-separated for Multiple DB Load Balancing)
# Example: "mongodb+srv://db1..., mongodb+srv://db2..."
DB_URIS = os.environ.get("DB_URI", "").split(",")
DB_NAME = os.environ.get("DB_NAME", "TituSaveBot")

# Waiting time in seconds between message batches to prevent FloodWait
WAITING_TIME = int(os.environ.get("WAITING_TIME", "5"))

# Error reporting setting
ERROR_MESSAGE = bool(os.environ.get('ERROR_MESSAGE', True))