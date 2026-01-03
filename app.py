import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError
from cn_kangxi import kangxi_stroke

app = Flask(__name__)

# 從環境變數讀取 LINE 的金鑰 (等一下在 Render 設定)
line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

# --- 核心邏輯區 ---

def get_element(number):
    """數字轉五行"""
    last_digit = int(str(number)[-1])
    map_dict = {
        1: '木', 2: '木', 3: '火', 4: '火',
        5: '土', 6: '土', 7: '金', 8: '金',
        9: '水', 0: '水'
    }
    return map_dict.get(last_digit, '未知')

def get_nayin(year):
    """簡易納音查詢 (範圍 1924-2043)"""
    # 這裡為了節省篇幅，列出常用的年份對照。
    # 納音是60年一輪，1924是甲子年(海中金)。
    nayins = [
        "海中金","海中金","爐中火","爐中火","大林木","大林木","路旁土","路旁土","劍鋒金","劍鋒金",
        "山頭火","山頭火","澗下水","澗下水","城頭土","城頭土","白蠟金","白蠟金","楊柳木","楊柳木",
        "泉中水","泉中水","屋上土","屋上土","霹靂火","霹靂火","松柏木","松柏木","長流水","長流水",
        "沙中金","沙中金","山下火","山下火","平地木","平地木","壁上土","壁上土","金箔金","金箔金",
        "覆燈火","覆燈火","天河水","天河水","大驛土","大驛土","釵釧金","釵釧金","桑柘木","桑柘木",
        "大溪水","大溪水","沙中土","沙中土","天上火","天上火","石榴木","石榴木","大海水","大海水"
    ]
    try:
        y = int(year)
        # 1924 是甲子年，索引為 0
        idx = (y - 1924) % 60
        return nayins[idx]
    except:
        return "未知"

def analyze_name(full_name, birth_year):
    # 複姓列表
    compound_surnames = ["歐陽", "太史", "端木", "上官", "司馬", "東方", "獨孤", "南宮", "萬俟", "聞人", "夏侯", "諸葛", "尉遲", "公羊", "赫連", "澹台", "皇甫", "宗政", "濮陽", "公冶", "太叔", "申屠", "公孫", "慕容", "仲孫", "鐘離", "長孫", "宇文", "司徒", "鮮于", "司空", "閭丘", "子車", "亓官", "司寇", "巫馬", "公西", "顓孫", "壤駟", "公良", "漆雕", "樂正", "宰父", "穀梁", "拓跋", "夾谷", "軒轅", "令狐", "段干", "百里", "呼延", "東郭", "南門", "羊舌", "微生", "公戶", "公玉", "公儀", "梁丘", "公仲", "公上", "公門", "公山", "公堅", "左丘", "公伯", "西門", "公祖", "第五", "公乘", "貫丘", "公晰", "南榮", "東里", "東宮", "仲長", "子書", "子桑", "即墨", "達奚", "褚師", "吳銘"]
    
    surname = ""
    name = ""
    
    # 切分姓與名
    if len(full_name) >= 2 and full_name[:2] in compound_surnames:
        surname = full_name[:2]
        name = full_name[2:]
    else:
        surname = full_name[:1]
        name = full_name[1:]
        
    if not name: return "請輸入完整姓名"

    # 查筆畫 (使用 cn_kangxi)
    s_strokes = [kangxi_stroke(c) for c in surname]
    n_strokes = [kangxi_stroke(c) for c in name]
    
    # 變數
    tian, ren, di, wai = 0, 0, 0, 0
    is_compound = len(surname) > 1
    is_single_name = len(name) == 1
    
    # 天格
    tian = sum(s_strokes) if is_compound else (s_strokes[0] + 1)
    
    # 人格 (姓最末 + 名首)
    ren = s_strokes[-1] + n_strokes[0]
    
    # 地格
    di = (n_strokes[0] + 1) if is_single_name else sum(n_strokes[:2])
    
    # 外格
    if is_single_name:
        wai = 2 # 單名外格固定為木(2)
    else:
        # 雙名: 名尾字+1 (此為通用規則，若需複姓雙名特殊處理可在此修改)
        wai = n_strokes[-1] + 1

    # 回傳結果
    return (
        f"【{full_name}】格局分析\n"
        f"出生年納音：{get_nayin(birth_year)}\n"
        f"----------------\n"
        f"天格：{tian} ({get_element(tian)})\n"
        f"人格：{ren} ({get_element(ren)})\n"
        f"地格：{di} ({get_element(di)})\n"
        f"外格：{wai} ({get_element(wai)})"
    )

# --- LINE Bot 介面 ---

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()
    # 簡單防呆：檢查是否包含空格
    if " " in msg:
        try:
            parts = msg.split()
            if len(parts) >= 2:
                name_input = parts[0]
                year_input = parts[1]
                result = analyze_name(name_input, year_input)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=result))
        except Exception as e:
            print(e)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="計算發生錯誤，請稍後再試。"))
    else:
        # 如果用戶只輸入文字，沒有空格，提示用法
        line_bot_api.reply_message(
            event.reply_token, 
            TextSendMessage(text="請依照格式輸入：\n姓名 西元出生年\n(中間請空一格)\n\n範例：\n李大同 1990")
        )

if __name__ == "__main__":
    app.run()