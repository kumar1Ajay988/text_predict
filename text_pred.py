from flask import Flask, request, jsonify
import openai
import asyncio
import aiohttp
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

OPENAI_API_KEY = "5a60e1c154fa4563b37ca14a4a6c5a0f"

async def stream_prediction(text):
    """Handles real-time streaming of predictions."""
    prompt = f"Predict the next word for: '{text}' and provide three possible words."

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.openai.com/v1/chat/completions",
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 10,
                "stream": True
            },
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"}
        ) as response:
            async for chunk in response.content.iter_any():
                if chunk:
                    try:
                        decoded_chunk = chunk.decode("utf-8").strip()
                        if decoded_chunk:
                            socketio.emit("predict", {"data": decoded_chunk})  # Emit prediction
                    except Exception as e:
                        print(f"Error in streaming: {e}")
                        continue

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Flask Server Running with SocketIO!"})

@socketio.on("predict")
def handle_predict(data):
    """Handles incoming 'predict' events from SocketIO."""
    text = data.get("text", "")
    if text:
        socketio.start_background_task(stream_prediction, text)  # Start async task

if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=8080, debug=False)