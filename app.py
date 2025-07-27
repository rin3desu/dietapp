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
    conn.commit()
    conn.close()

init_db()  #アプリ起動時に1度だけ呼び出す


@app.route("/",methods=["GET","POST"])  # URLのルート("/")にアクセスしたときに実行される関数を指定
def index():
    weight = None
    date = None
    if request.method == "POST":
        weight = request.form.get("weight")
        date = request.form.get("date")
        if weight and date:
            with sqlite3.connect('diet.db') as conn:    
                cur = conn.cursor()
                cur.execute("INSERT INTO weights (date, weight) VALUES (?, ?)", (date,weight))
                conn.commit()
    
    #ここで履歴を取得（新しい順）            
    with sqlite3.connect('diet.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT date, weight FROM weights ORDER BY date DESC")
        records = cur.fetchall()
        
    return render_template("index.html",weight = weight, date = date, records = records)  # templates/index.htmlをブラウザに返す

if __name__ == "__main__":  # このファイルが直接実行された場合に以下を実行
    app.run(debug=True)  # 開発用サーバーを起動。debug=Trueで自動リロードや詳細エラー表示