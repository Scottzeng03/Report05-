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

# 儲存投票數
vote_counts = {"gemini": 0, "chatgpt": 0}

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
            model="gpt-4o",
            messages=[{"role": "user", "content": question}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"ChatGPT 錯誤: {e}")
        return "❌ 由於 ChatGPT 開發金鑰需要使用者付費，因此無法回覆，請付費後再試。"

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

        # 顯示投票輪播
        elif user_message == "vote":
            carousel_template = {
                "type": "carousel",
                "columns": [
                    {
                        "thumbnailImageUrl": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Google_Gemini_logo.svg/330px-Google_Gemini_logo.svg.png",
                        "title": "Gemini",
                        "text": "是由 Google 開發的生成式人工智慧聊天機器人。",
                        "actions": [
                            {
                                "type": "uri",
                                "label": "維基百科",
                                "uri": "https://zh.wikipedia.org/zh-tw/Gemini_(%E8%81%8A%E5%A4%A9%E6%A9%9F%E5%99%A8%E4%BA%BA)"
                            },
                            {
                                "type": "uri",
                                "label": "Youtube",
                                "uri": "https://www.youtube.com/watch?v=yOpfYMBocYI"
                            },
                            {
                                "type": "message",
                                "label": "投票",
                                "text": "我投Gemini一票"
                            }
                        ]
                    },
                    {
                        "thumbnailImageUrl": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ef/ChatGPT-Logo.svg/330px-ChatGPT-Logo.svg.png",
                        "title": "ChatGPT",
                        "text": "由 OpenAI 開發的人工智慧聊天機器人。",
                        "actions": [
                            {
                                "type": "uri",
                                "label": "維基百科",
                                "uri": "https://zh.wikipedia.org/zh-tw/ChatGPT"
                            },
                            {
                                "type": "uri",
                                "label": "Youtube",
                                "uri": "https://www.youtube.com/watch?v=WizoCwjEKsg"
                            },
                            {
                                "type": "message",
                                "label": "投票",
                                "text": "我投ChatGPT一票"
                            }
                        ]
                    }
                ]
            }
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        {
                            "type": "template",
                            "altText": "這是投票輪播",
                            "template": carousel_template
                        }
                    ]
                )
            )
            return

        # 記錄投票
        elif user_message == "我投gemini一票":
            vote_counts["gemini"] += 1
            reply_text = f"✅ 已為 Gemini 計票！目前 Gemini：{vote_counts['gemini']} 票，ChatGPT：{vote_counts['chatgpt']} 票。"
        elif user_message == "我投chatgpt一票":
            vote_counts["chatgpt"] += 1
            reply_text = f"✅ 已為 ChatGPT 計票！目前 Gemini：{vote_counts['gemini']} 票，ChatGPT：{vote_counts['chatgpt']} 票。"
        elif user_message == "reset vote":
            vote_counts["gemini"] = 0
            vote_counts["chatgpt"] = 0
            reply_text = "✅ 投票已重置。"

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
            reply_text = "請先輸入「hi ai」來選擇你想使用的 AI 模型，或輸入「vote」參與投票。"

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
