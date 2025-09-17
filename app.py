import os
import sqlite3
import click
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, g
from werkzeug.utils import secure_filename

# --- アプリケーションの初期化 ---
app = Flask(__name__)
app.config['DATABASE'] = 'diet.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# --- データベース接続の管理 ---

# リクエストごとにDB接続を確立し、gオブジェクトに格納する
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        # カラム名でデータにアクセスできるようにする
        g.db.row_factory = sqlite3.Row
    return g.db

# リクエスト終了時にDB接続を自動的に閉じる
@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- データベース初期化コマンド ---

# schema.sqlファイルからスキーマを読み込みDBを初期化する
def init_db():
    db = get_db()
    # schema.sqlファイルを開いて実行する
    with app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

# "flask init-db" というコマンドをターミナルで実行できるようにする
@app.cli.command('init-db')
def init_db_command():
    """既存のデータをクリアし、新しいテーブルを作成します。"""
    init_db()
    click.echo('データベースの初期化が完了しました。')


# --- ルート（URLと関数の対応付け） ---

# 1. トップページ（玄関ページ）
@app.route('/')
def index():
    """アプリのトップページを表示します。"""
    return render_template('index.html')

# 2. 体重記録ページ（データの表示と追加）
@app.route('/weight', methods=['GET', 'POST'])
def weight_page():
    """体重の記録と履歴・グラフの表示を行います。"""
    db = get_db()
    
    # [POST] フォームからデータが送信された場合の処理
    if request.method == 'POST':
        weight = request.form.get("weight")
        date = request.form.get("date")
        
        # 簡単なバリデーション
        if weight and date:
            full_datetime = f"{date} {datetime.now().strftime('%H:%M:%S')}"
            db.execute(
                'INSERT INTO weights (date, weight) VALUES (?, ?)',
                (full_datetime, float(weight))
            )
            db.commit()
        # 記録後は、同じ体重ページにリダイレクトして結果を表示する
        return redirect(url_for('weight_page'))

    # [GET] ページを通常表示する場合の処理
    # 履歴表示用のデータを取得
    weight_records = db.execute('SELECT date, weight FROM weights ORDER BY date DESC').fetchall()
    
    # グラフ表示用のデータを取得
    graph_data = db.execute(
        'SELECT STRFTIME("%Y-%m-%d", date) as day, MIN(weight) as min_weight '
        'FROM weights GROUP BY day ORDER BY day'
    ).fetchall()
    
    dates = [row['day'] for row in graph_data]
    weights = [row['min_weight'] for row in graph_data]
    
    return render_template('weight.html', records=weight_records, dates=dates, weights=weights)

# 3. 食事記録ページ（一覧表示）
@app.route('/meal')
def meal_page():
    """食事記録の一覧を表示します。"""
    db = get_db()
    meals = db.execute('SELECT * FROM meals ORDER BY date DESC, id DESC').fetchall()
    return render_template('meal.html', meals=meals)

# 4. 食事記録フォーム表示
@app.route('/meal_form')
def meal_form():
    """食事を記録するためのフォームページを表示します。"""
    return render_template('meal_form.html')

# 5. 食事データの追加処理
@app.route('/add_meal', methods=['POST'])
def add_meal():
    """食事フォームから送信されたデータをDBに保存します。"""
    date = request.form['date']
    time_slot = request.form['time_slot']
    content = request.form['content']
    ingredients = request.form.get('ingredients')
    photo = request.files.get('image')
    
    photo_path = None
    if photo and photo.filename:
        filename = secure_filename(photo.filename)
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        photo.save(photo_path)
    
    db = get_db()
    db.execute(
        'INSERT INTO meals (date, time_slot, content, ingredients, image_path) VALUES (?, ?, ?, ?, ?)',
        (date, time_slot, content, ingredients, photo_path)
    )
    db.commit()
    # 記録後は、食事一覧ページにリダイレクトする
    return redirect(url_for('meal_page'))


# --- アプリケーションの実行 ---
if __name__ == "__main__":
    app.run(debug=True)