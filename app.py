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

# ChatGPT (OpenAI) SDK
import openai

# 初始化 Flask 應用
app = Flask(__name__)

# 設定 LINE Messaging API
configuration = Configuration(access_token=os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
line_handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# 設定 Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

# 設定 OpenAI 客戶端（新版 SDK）
openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 儲存使用者選擇的 AI 模型
user_model_choice = {}

# Gemini 回答函式
def ask_gemini(question):
    try:
        response = gemini_model.generate_content(question)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini 錯誤: {e}")
        return "❌ Gemini 回覆失敗，請稍後再試。"

# ChatGPT 回答函式
def ask_chatgpt(question):
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",  # 也可以換成 "gpt-4-turbo" 或 "gpt-3.5-turbo"
            messages=[{"role": "user", "content": question}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"ChatGPT 錯誤: {e}")
        return "❌ ChatGPT 回覆失敗，請稍後再試。"

# Webhook 路由
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 處理使用者訊息
@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text.lower().strip()

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        # 使用者輸入 hi ai → 顯示選擇 AI 模型的選單
        if user_message == "hi ai":
            confirm_template = ConfirmTemplate(
                text="請選擇你想要的 AI 模型：",
                actions=[
                    MessageAction(label="Gemini", text="使用 Gemini"),
                    MessageAction(label="ChatGPT", text="使用 ChatGPT")
                ]
            )
            template_message = TemplateMessage(
                alt_text="請選擇 AI 模型",
                template=confirm_template
            )
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[template_message]
                )
            )
            return

        # 記錄使用者選擇的模型
        elif user_message == "使用 gemini":
            user_model_choice[user_id] = "gemini"
            reply_text = "✅ 你已選擇 Gemini，可以開始對話了！"
        elif user_message == "使用 chatgpt":
            user_model_choice[user_id] = "chatgpt"
            reply_text = "✅ 你已選擇 ChatGPT，可以開始對話了！"

        # 根據使用者已選擇的模型來回覆
        elif user_id in user_model_choice:
            model = user_model_choice[user_id]
            if model == "gemini":
                reply_text = ask_gemini(user_message)
            else:
                reply_text = ask_chatgpt(user_message)
        else:
            # 尚未選擇模型
            reply_text = "請先輸入「hi ai」來選擇你想使用的 AI 模型。"

        # 傳送回覆
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

# 執行伺服器
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
