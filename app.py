import sqlite3
from flask import Flask, render_template, request
from datetime import datetime

app = Flask(__name__)  # Flaskアプリケーションのインスタンスを作成

def init_db():
    conn = sqlite3.connect('diet.db')
    cur = conn.cursor()
    cur.execute('''
            CREATE TABLE IF NOT EXISTS weights(
            id  INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            weight REAL NOT NULL
            )
        ''')
    
    # 食事テーブルを作成（まだ存在しない場合のみ）
    cur.execute("""
    CREATE TABLE IF NOT EXISTS meals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        time_slot TEXT NOT NULL,
        content TEXT NOT NULL,
        ingredients TEXT,
        image_path TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()  #アプリ起動時に1度だけ呼び出す


@app.route("/",methods=["GET","POST"])  # URLのルート("/")にアクセスしたときに実行される関数を指定
def index():
    weight = None
    date = None
    
    if request.method == "POST":
        weight = request.form.get("weight")
        date_part = request.form.get("date") 
        
        #送信された日付に現在の時刻
        now_time = datetime.now().strftime("%H:%M:%S")
        full_datetime = f"{date_part} {now_time}"
        
        try:
            # sqlite3.connect() as connによって自動でconn.commit()とconn.close()をしてくれる
            with sqlite3.connect('diet.db') as conn:
                cur = conn.cursor()
                cur.execute("INSERT INTO weights (date, weight) VALUES (?, ?)", (full_datetime,weight))
                conn.commit()
        except sqlite3.OperationalError as e:
            return f"エラーが発生しました: {e}"
    try:
        with sqlite3.connect('diet.db') as conn:
            cur = conn.cursor()
    # 同じ日付の場合、その日付の最小値の体重をとってくる
            cur.execute("""
                SELECT date,MIN(weight) 
                FROM weights 
                GROUP BY date
                ORDER BY date
            """)
            data = cur.fetchall()
            cur.execute("SELECT date, weight FROM weights ORDER BY date DESC")
            records = cur.fetchall()
    except sqlite3.OperationalError as e:
        return f"エラーが発生しました： {e}" 
    
    dates = [row[0] for row in data]
    weights = [row[1] for row in data]
    
    #ここで履歴を取得（新しい順）            
    with sqlite3.connect('diet.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT date, weight FROM weights ORDER BY date DESC")
        records = cur.fetchall()
        
    return render_template("index.html",weight = weight, date = date,dates=dates,weights =weights ,records = records)  # templates/index.htmlをブラウザに返す

if __name__ == "__main__":  # このファイルが直接実行された場合に以下を実行
    app.run(debug=True)  # 開発用サーバーを起動。debug=Trueで自動リロードや詳細エラー表示