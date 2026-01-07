from flask import Flask, request
import os
from linebot import LineBotApi, WebhookParser
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError

app = Flask(__name__)

# 從環境變數讀取，不要寫死在程式裡，才不會在 GitHub 外流
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
TARGET_SOURCE_ID = os.getenv("TARGET_SOURCE_ID", "")  # 可留空=全部來源都生效

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    # 在 Render 還沒設定環境變數前，程式可能啟動但不能正常處理事件
    print("WARNING: CHANNEL_ACCESS_TOKEN or CHANNEL_SECRET is not set.")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN) if CHANNEL_ACCESS_TOKEN else None
parser = WebhookParser(CHANNEL_SECRET) if CHANNEL_SECRET else None

# ===== 你要的關鍵字規則在這裡改 =====
KEYWORD_RULES = [
    {
        "keywords": ["幹", "靠北", "三小"],
        "reply": "⚠️ 請注意用詞，本群禁止不當言論。"
    },
    {
        "keywords": ["詐騙", "投資保證"],
        "reply": "⚠️ 這可能涉及詐騙，請提高警覺。"
    }
]


def match_rule(text: str):
    """回傳第一個命中的規則，沒有就回 None"""
    for rule in KEYWORD_RULES:
        for kw in rule["keywords"]:
            if kw and kw in text:
                return rule
    return None


@app.route("/callback", methods=["POST"])
def callback():
    if parser is None or line_bot_api is None:
        # 尚未正確設定 token / secret
        return "Bot not configured", 200

    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        return "Signature error", 400
    except Exception as e:
        print(f"Parse error: {e}")
        return "Parse error", 400

    for event in events:
        if isinstance(event, MessageEvent) and isinstance(event.message, TextMessage):
            source = event.source

            # 取得來源 ID
            if source.type == "group":
                source_id = source.group_id
            elif source.type == "room":
                source_id = source.room_id
            else:
                source_id = source.user_id

            text = event.message.text.strip()

            # 特殊指令：!id → 回傳來源類型與 ID，方便你設定 TARGET_SOURCE_ID
            if text == "!id":
                reply_text = f"Source type: {source.type}\nID: {source_id}"
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=reply_text)
                )
                continue

            # 若有設定 TARGET_SOURCE_ID，就只處理指定來源
            if TARGET_SOURCE_ID and TARGET_SOURCE_ID != source_id:
                continue

            # 關鍵字比對
            rule = match_rule(text)
            if rule:
                reply = rule["reply"]
                try:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=reply)
                    )
                except Exception as e:
                    print(f"Send message error: {e}")

    return "OK"


@app.route("/")
def index():
    return "LINE noscambot is running."


if __name__ == "__main__":
    # Render 會提供 PORT 環境變數，沒有時就用 10000（本機測試用）
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
