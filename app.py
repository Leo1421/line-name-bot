import os
import json
import re
import logging
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, FlexSendMessage
from linebot.exceptions import InvalidSignatureError

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

KANGXI_JSON_PATH = os.path.join(os.path.dirname(__file__), "kangxi_total_strokes_kv.json")
try:
    with open(KANGXI_JSON_PATH, "r", encoding="utf-8") as f:
        STROKE_DICT = json.load(f)
except Exception:
    STROKE_DICT = {}

DOUBLE_SURNAME_LIST = [
    "張簡","歐陽","范姜","周黃","張廖","張李","張許","張陳",
    "諸葛","司馬","司徒","上官","端木","皇甫","尉遲","公孫",
    "令狐","鍾離","宇文","東方","南宮","長孫","夏侯","濮陽"
]

def get_stroke_count(c):
    return STROKE_DICT.get(c, 10)

def get_element(n):
    return {0:'水',1:'木',2:'木',3:'火',4:'火',5:'土',6:'土',7:'金',8:'金',9:'水'}[int(str(n)[-1])]

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()
    match = re.match(r"([^\d\+\s\-]+)[\+\s\-]*(\d*)", msg)
    if not match:
        return

    full_name = match.group(1)

    if (len(full_name) >= 3 and full_name[:2] in DOUBLE_SURNAME_LIST):
        surname, name_part = full_name[:2], full_name[2:]
    else:
        surname, name_part = full_name[:1], full_name[1:]

    s = [get_stroke_count(c) for c in surname]
    n = [get_stroke_count(c) for c in name_part] or [10]

    zong = sum(s) + sum(n)
    tian = sum(s) if len(surname) > 1 else s[0] + 1
    ren = s[-1] + n[0]
    di = n[0] + 1 if len(n) == 1 else sum(n)
    wai = zong - ren + 1

    name_boxes = [{
        "type": "box",
        "layout": "horizontal",
        "contents": [
            {"type":"text","text":c,"size":"xxl","weight":"bold","align":"center","flex":1},
            {"type":"text","text":str(get_stroke_count(c)),"size":"xxs","color":"#666","position":"absolute","offsetTop":"12px","offsetStart":"65%"}
        ]
    } for c in full_name]

    flex = {
        "type": "bubble",
        "size": "mega",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [

                # ===== 上排 =====
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "vertical",
                            "flex": 1,
                            "contents": [
                                {"type":"text","text":"外格","size":"xxs","align":"center"},
                                {"type":"text","text":get_element(wai),"weight":"bold","align":"center"}
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "flex": 2,
                            "contents": name_boxes
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "flex": 1,
                            "contents": [
                                {"type":"text","text":"天格","size":"xxs","align":"center"},
                                {"type":"text","text":get_element(tian),"weight":"bold","align":"center"},
                                {"type":"text","text":"人格","size":"xxs","align":"center"},
                                {"type":"text","text":get_element(ren),"weight":"bold","align":"center"},
                                {"type":"text","text":"地格","size":"xxs","align":"center"},
                                {"type":"text","text":get_element(di),"weight":"bold","align":"center"}
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "flex": 1,
                            "contents": [
                                {"type":"text","text":"出生年","size":"xxs","align":"center"},
                                {"type":"text","text":"--","align":"center"}
                            ]
                        }
                    ]
                },

                # ===== 分隔線（整排）=====
                {
                    "type": "separator",
                    "margin": "lg"
                },

                # ===== 下排：只在三才欄出現總格 =====
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type":"box","layout":"vertical","flex":1,"contents":[]},
                        {"type":"box","layout":"vertical","flex":2,"contents":[]},
                        {
                            "type": "box",
                            "layout": "vertical",
                            "flex": 1,
                            "contents": [
                                {"type":"text","text":"總格","size":"xxs","align":"center"},
                                {"type":"text","text":get_element(zong),"weight":"bold","align":"center"}
                            ]
                        },
                        {"type":"box","layout":"vertical","flex":1,"contents":[]}
                    ]
                }
            ]
        }
    }

    line_bot_api.reply_message(
        event.reply_token,
        FlexSendMessage(alt_text=f"{full_name} 命格解析", contents=flex)
    )

@app.route("/callback", methods=["POST"])
def callback():
    handler.handle(
        request.get_data(as_text=True),
        request.headers["X-Line-Signature"]
    )
    return "OK"

if __name__ == "__main__":
    app.run()
