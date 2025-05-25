# -*- coding: utf-8 -*-
import os
from flask import Flask, request, abort

# LINE Bot SDK
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest,
    TextMessage
)

# Gemini SDK
import google.generativeai as genai

# 初始化 Flask 應用
app = Flask(__name__)

# 設定 LINE Messaging API
configuration = Configuration(access_token=os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
line_handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# 設定 Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

# Gemini 問答函式
def ask_gemini(question):
    try:
        response = gemini_model.generate_content(question)
        return response.text.strip()
    except Exception as e:
        return "很抱歉，AI 回覆失敗。請稍後再試。"

# LINE Webhook 入口
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 處理訊息事件，使用 Gemini 回覆
@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_message = event.message.text
    ai_reply = ask_gemini(user_message)
    
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=ai_reply)]
            )
        )

# 執行應用
if __name__ == "__main__":
    app.run()
