import keyboard
import pyperclip
import requests
import time
import re
import json
import os


# Вставь сюда свой API-ключ от провайдера (routerai.ru, OpenAI или другой OpenAI-совместимый)
API_KEY = ""
# При необходимости поменяй URL и модель под своего провайдера
API_URL = "https://routerai.ru/api/v1/chat/completions"
MODEL = "deepseek/deepseek-v3.2"


HISTORY_FILE = "chat_history.json"
MAX_TURNS = 12


SESSION = requests.Session()
SESSION.trust_env = False


def strip_markdown(text: str) -> str:
    text = re.sub(r"`.*?```", "", text, flags=re.S)
    text = text.replace("`", "")
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    text = text.replace("**", "").replace("__", "")
    text = text.replace("*", "").replace("_", "")

    text = re.sub(r"(?m)^\s*#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*[-*+]\s+", "", text)

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return [{"role": "system", "content": "Отвечай обычным текстом без markdown (без **, *, #)."}]
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list) or len(data) == 0:
            raise ValueError("bad history")
        return data
    except Exception:
        return [{"role": "system", "content": "Отвечай обычным текстом без markdown (без **, *, #)."}]


def save_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def trim_history(history):
    if not history:
        return history

    system = history[0] if history[0].get("role") == "system" else None
    rest = history[1:] if system else history

    max_msgs = 2 * MAX_TURNS
    if len(rest) > max_msgs:
        rest = rest[-max_msgs:]

    return [system] + rest if system else rest


CHAT_HISTORY = load_history()


def ask_ai(messages):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json; charset=utf-8",
    }

    payload = {
        "model": MODEL,
        "max_tokens": 700,
        "messages": messages,
    }

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    resp = SESSION.post(API_URL, headers=headers, data=body, timeout=25)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def on_hotkey_pressed():
    global CHAT_HISTORY

    time.sleep(0.1)

    copied_text = pyperclip.paste()
    if not copied_text or not copied_text.strip():
        return

    keyboard.write("...")

    CHAT_HISTORY.append({"role": "user", "content": copied_text})
    CHAT_HISTORY = trim_history(CHAT_HISTORY)

    try:
        ai_response = ask_ai(CHAT_HISTORY)
    except Exception as e:
        keyboard.press_and_release("backspace")
        keyboard.press_and_release("backspace")
        keyboard.press_and_release("backspace")
        keyboard.write("!")
        pyperclip.copy(f"Ошибка запроса: {e}")
        return

    ai_response = strip_markdown(ai_response)

    CHAT_HISTORY.append({"role": "assistant", "content": ai_response})
    CHAT_HISTORY = trim_history(CHAT_HISTORY)
    save_history(CHAT_HISTORY)

    keyboard.press_and_release("backspace")
    keyboard.press_and_release("backspace")
    keyboard.press_and_release("backspace")

    keyboard.write("!")
    pyperclip.copy(ai_response)


keyboard.add_hotkey("ctrl+shift+q", on_hotkey_pressed)
keyboard.wait()
