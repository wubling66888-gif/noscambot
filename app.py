from flask import Flask, request
import os
from linebot import LineBotApi, WebhookParser
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(CHANNEL_SECRET)

TARGET_SOURCE_ID = os.getenv("TARGET_SOURCE_ID", "")  # 可選，留空=全部群

# ===== 你要的關鍵字規則在這裡改 =====
KEYWORD_RULES = [
    {
        "keywords": ["幹", "靠北", "三小"],
        "reply": "⚠️ 請注意用詞，本群禁止不當言論"
    },
    {
        "keywords": ["詐騙", "投資保證"],
        "reply": "⚠️ 這可能涉及詐騙，請提高警覺"
    }
]


def match_rule(text):
    for rule in KEYWORD_RULES:
        for kw in rule["keywords"]:
            if kw in text:
                return rule
    return None


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        return "Signature error", 400

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

            # 若設定特定群，且不符合 → 忽略
            if TARGET_SOURCE_ID and TARGET_SOURCE_ID != source_id:
                continue

            text = event.message.text
            rule = match_rule(text)

            if rule:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=rule["reply"])
                )

    return "OK"


@app.route("/")
def hello():
    return "LINE Bot running."


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
