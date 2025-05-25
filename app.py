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
    TextMessage,
    TemplateMessage,
    ConfirmTemplate,
    MessageAction
)

# Gemini SDK
import google.generativeai as genai

# ChatGPT SDK（你需安裝 openai）
import openai
openai.api_key = os.getenv("OPENAI_API_KEY")  # [新增] ChatGPT 的 API 金鑰

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
        return "很抱歉，Gemini 回覆失敗。請稍後再試。"

# [新增] ChatGPT 問答函式
def ask_chatgpt(question):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # 或 "gpt-3.5-turbo"
            messages=[{"role": "user", "content": question}]
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return "很抱歉，ChatGPT 回覆失敗。請稍後再試。"

# [新增] 儲存使用者選擇的模型
user_model_choice = {}

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

# 處理訊息事件
@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text.strip().lower()

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        # [新增] 若使用者輸入 hi ai，顯示選擇視窗
        if user_message == "hi ai":
            confirm_template = ConfirmTemplate(
                text="請選擇你想使用的 AI 模型：",
                actions=[
                    MessageAction(label="Gemini", text="使用 Gemini"),
                    MessageAction(label="ChatGPT", text="使用 ChatGPT")
                ]
            )
            reply = TemplateMessage(
                alt_text="請選擇 AI 模型",
                template=confirm_template
            )
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[reply]
                )
            )
            return

        # [新增] 使用者選擇模型
        if user_message == "使用 gemini":
            user_model_choice[user_id] = "gemini"
            reply_text = "你已選擇 Gemini，請開始提問。"
        elif user_message == "使用 chatgpt":
            user_model_choice[user_id] = "chatgpt"
            reply_text = "你已選擇 ChatGPT，請開始提問。"
        # [新增] 若已選擇模型則回覆
        elif user_id in user_model_choice:
            model = user_model_choice[user_id]
            if model == "gemini":
                reply_text = ask_gemini(user_message)
            else:
                reply_text = ask_chatgpt(user_message)
        else:
            reply_text = "請先輸入「hi ai」來選擇要對話的 AI 模型。"

        # 回覆訊息
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

# 執行應用
if __name__ == "__main__":
    app.run()
