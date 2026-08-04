from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return 'Titu Bot is Running Alive!'

if __name__ == "__main__":
    app.run()