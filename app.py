# for colab
from google.colab import userdata
from pyngrok import ngrok
from flask_ngrok import run_with_ngrok
def ngrok_start():
    ngrok.set_auth_token(userdata.get('NGROK_AUTHTOKEN'))
    ngrok.connect(5000)
    run_with_ngrok(app)

from flask import Flask, request, abort

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    TemplateMessage,
    ConfirmTemplate,
    MessageAction,
    CarouselTemplate,
    CarouselColumn,
    URIAction
)

# Gemini AI
import google.generativeai as genai
genai.configure(api_key=userdata.get("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

# OpenAI ChatGPT
import openai
openai.api_key = userdata.get("OPENAI_API_KEY")

app = Flask(__name__)

@app.route("/", methods=['GET'])
def index():
  return "Hello!"

configuration = Configuration(access_token=userdata.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(userdata.get('LINE_CHANNEL_SECRET'))

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# Gemini 回覆
def ask_gemini(prompt):
    try:
        response = gemini_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return "Gemini 發生錯誤，請稍後再試。"

# ChatGPT 回覆
def ask_chatgpt(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return "ChatGPT 發生錯誤，請稍後再試。"

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_text = event.message.text.lower().strip()

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        if user_text == "hi ai":
            # 顯示選擇視窗
            confirm_template = ConfirmTemplate(
                text="請選擇想使用的 AI 模型",
                actions=[
                    MessageAction(label="Gemini", text="使用 Gemini"),
                    MessageAction(label="ChatGPT", text="使用 ChatGPT")
                ]
            )
            reply = TemplateMessage(
                alt_text="選擇 AI 模型",
                template=confirm_template
            )

        elif user_text == "使用 gemini":
            ai_reply = ask_gemini("你好，我想和你聊天")
            reply = TextMessage(text=ai_reply)

        elif user_text == "使用 chatgpt":
            ai_reply = ask_chatgpt("你好，我想和你聊天")
            reply = TextMessage(text=ai_reply)

        elif user_text == "confirm":
            template = ConfirmTemplate(
                text="你喜歡葬送的福利連嗎？",
                actions=[
                    MessageAction(label="是", text="我超愛"),
                    MessageAction(label="否", text="其實我很愛，但我要傲嬌的說不")
                ]
            )
            reply = TemplateMessage(
                alt_text="這是確認視窗",
                template=template
            )

        elif user_text == "carousel":
            Carousel_template = CarouselTemplate(
                columns=[
                    CarouselColumn(
                        thumbnail_image_url='https://upload.wikimedia.org/wikipedia/zh/7/7d/Summer_Wars_poster.jpg',
                        title='夏日大作戰',
                        text='細田守執導的的日本科幻暨浪漫電影',
                        actions=[
                            URIAction(label='維基百科', uri='https://zh.wikipedia.org/zh-tw/%E5%A4%8F%E6%97%A5%E5%A4%A7%E4%BD%9C%E6%88%B0'),
                            URIAction(label='Youtube', uri='https://www.youtube.com/watch?v=r8Ionf7_qBM'),
                            MessageAction(label="投票", text="我投夏日大作戰一票")
                        ]
                    ),
                    CarouselColumn(
                        thumbnail_image_url='https://upload.wikimedia.org/wikipedia/zh/4/4f/Castle_of_Cagliostro_poster.png',
                        title='魯邦三世 卡里奧斯特羅城',
                        text='宮崎駿執導的日本動畫動作冒險喜劇電影',
                        actions=[
                            URIAction(label='維基百科', uri='https://zh.wikipedia.org/zh-tw/%E9%AD%AF%E9%82%A6%E4%B8%89%E4%B8%96_%E5%8D%A1%E9%87%8C%E5%A5%A7%E6%96%AF%E7%89%B9%E7%BE%85%E4%B9%8B%E5%9F%8E'),
                            URIAction(label='Youtube', uri='https://www.youtube.com/watch?v=BO0iwApfDr8'),
                            MessageAction(label="投票", text="我投魯邦三世 卡里奧斯特羅城一票")
                        ]
                    )
                ]
            )
            reply = TemplateMessage(
                alt_text='這是輪播視窗',
                template=Carousel_template
            )

        else:
            reply = TextMessage(text="輸入 'hi ai' 試試看使用 AI 對話！")

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[reply]
            )
        )

# 啟動伺服器
ngrok_start()
if __name__ == "__main__":
    app.run()
