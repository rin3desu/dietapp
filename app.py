import os
import sqlite3
import click
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, g, flash
from werkzeug.utils import secure_filename

# --- アプリケーションの初期化 ---
app = Flask(__name__)
app.secret_key = 'Kinchan_3110'
app.config['DATABASE'] = 'diet.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# --- データベース接続の管理 ---

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- データベース初期化コマンド ---

def init_db():
    db = get_db()
    with app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

@app.cli.command('init-db')
def init_db_command():
    """既存のデータをクリアし、新しいテーブルを作成します。"""
    init_db()
    click.echo('データベースの初期化が完了しました。')


# --- ルート（URLと関数の対応付け） ---

@app.route('/')
def index():
    """アプリのトップページを表示します。"""
    return render_template('index.html')


@app.route('/weight', methods=['GET', 'POST'])
def weight_page():
    """体重の記録と履歴・グラフの表示を行います。"""
    db = get_db()
    
    if request.method == 'POST':
        weight_str = request.form.get("weight")
        date_str = request.form.get("date")
        
        if not date_str:
            flash('日付を入力してください')
            return redirect(url_for('weight_page'))
        
        if not weight_str:
            flash('体重を入力してください')
            return redirect(url_for('weight_page'))
        
        try:
            weight = float(weight_str)
        except ValueError:
            flash('体重には半角数字を入力してください')
            return redirect(url_for('weight_page'))
        
        # 【修正点1】f-string (f"...") を使うように修正
        full_datetime = f"{date_str} {datetime.now().strftime('%H:%M:%S')}"
        
        db.execute(
            'INSERT INTO weights (date, weight) VALUES (?, ?)',
            (full_datetime, weight)
        )
        db.commit()
        flash('体重を記録しました!')
        return redirect(url_for('weight_page'))
    #ここから体重の前日比を表示
    #1. 日付順（古い順）にデータを取得
    weight_records_asc = db.execute('SELECT date, weight FROM weights ORDER BY date ASC').fetchall()
    
    #2. 前日比を計算して新しいリストを作成
    records_with_diff = []
    for i, record in enumerate(weight_records_asc):
        record_dict = dict(record)
        if i > 0:
            previous_record = weight_records_asc[i-1]
            difference = record['weight'] - previous_record['weight']
            record_dict['difference'] = difference
        else:
            record_dict['difference'] = None
        
        records_with_diff.append(record_dict)
        
    records_with_diff.reverse()
    
    graph_data = db.execute(
        'SELECT STRFTIME("%Y-%m-%d", date) as day, MIN(weight) as min_weight '
        'FROM weights GROUP BY day ORDER BY day'
    ).fetchall()
    
    dates = [row['day'] for row in graph_data]
    weights = [row['min_weight'] for row in graph_data]
    
    # テンプレートには前日比計算済みのリストを渡す
    return render_template('weight.html', records=records_with_diff, dates=dates, weights=weights)
    
    

@app.route('/meal')
def meal_page():
    """食事記録の一覧を表示します。"""
    db = get_db()
    meals = db.execute('SELECT * FROM meals ORDER BY date DESC, id DESC').fetchall()
    return render_template('meal.html', meals=meals)


@app.route('/meal_form')
def meal_form():
    """食事を記録するためのフォームページを表示します。"""
    return render_template('meal_form.html')


@app.route('/add_meal', methods=['POST'])
def add_meal():
    """食事フォームから送信されたデータをDBに保存します。"""
    date = request.form.get('date')
    time_slot = request.form.get('time_slot')
    content = request.form.get('content')
    ingredients = request.form.get('ingredients')
    photo = request.files.get('image')
    
    # 【修正点2】食事記録にもバリデーションを追加
    if not all([date, time_slot, content]):
        flash('日付、時間帯、食べたものは必須項目です。')
        return redirect(url_for('meal_form'))
    
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
    flash('食事を記録しました！')
    return redirect(url_for('meal_page'))


@app.route('/training', methods=['GET', 'POST'])
def training_page():
    """トレーニングの記録と履歴の表示を行います。"""
    db = get_db()
    
    if request.method == 'POST':
        date = request.form.get("date")
        event = request.form.get("event")
        part = request.form.get("part")
        reps_str = request.form.get("reps")
        sets_str = request.form.get("sets")
        
        if not all([date, event, part, reps_str, sets_str]):
            flash('すべての項目を入力してください。')
            return redirect(url_for('training_page'))

        try:
            reps = int(reps_str)
            sets = int(sets_str)
        except ValueError:
            flash('Rep数とセット数には半角数字を入力してください。')
            return redirect(url_for('training_page'))
        
        db.execute(
            'INSERT INTO trainings (date, event, part, reps, sets) VALUES (?, ?, ?, ?, ?)',
            (date, event, part, reps, sets)
        )
        db.commit()
        flash('トレーニングを記録しました！')
        return redirect(url_for('training_page'))
    
    filter_part = request.args.get('filter_part', '')

    trainings = db.execute('SELECT * FROM trainings ORDER BY date DESC, id DESC').fetchall()
    return render_template('training.html', trainings=trainings)


if __name__ == "__main__":
    app.run(debug=True)