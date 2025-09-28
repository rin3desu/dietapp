import os
import sqlite3
import click
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, g, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

# --- アプリケーションの初期化 ---
app = Flask(__name__)
app.secret_key = 'your_super_secret_key' # 必ず複雑なキーに変更してください
app.config['DATABASE'] = os.path.join('/var/data', 'diet.db') # Renderの永続ディスクパス
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# --- データベース接続の管理 ---
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'], detect_types=sqlite3.PARSE_DECLTYPES)
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
    init_db()
    click.echo('データベースの初期化が完了しました。')

# --- ユーザー認証 ---

# リクエストの前に、ログインしているユーザー情報を読み込む
@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

# ログインが必要なページ用のデコレータ
def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash('このページにアクセスするにはログインが必要です。')
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

# ユーザー登録
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        db = get_db()
        error = None

        if not username: error = 'ユーザー名は必須です。'
        elif not password: error = 'パスワードは必須です。'
        elif db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone() is not None:
            error = f"ユーザー名 {username} は既に使用されています。"

        if error is None:
            db.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, generate_password_hash(password)))
            db.commit()
            flash('登録が完了しました。ログインしてください。')
            return redirect(url_for('login'))
        flash(error)
    return render_template('register.html')

# ログイン
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        db = get_db()
        error = None
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

        if user is None:
            error = 'ユーザー名が正しくありません。'
        elif not check_password_hash(user['password_hash'], password):
            error = 'パスワードが正しくありません。'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            flash('ログインしました。')
            return redirect(url_for('index'))
        flash(error)
    return render_template('login.html')

# ログアウト
@app.route('/logout')
def logout():
    session.clear()
    flash('ログアウトしました。')
    return redirect(url_for('index'))

# --- メイン機能 ---

# トップページ
@app.route('/')
def index():
    return render_template('index.html')

# 体重記録ページ
@app.route('/weight', methods=['GET', 'POST'])
@login_required
def weight_page():
    user_id = g.user['id']
    db = get_db()
    
    if request.method == 'POST':
        weight_str = request.form.get("weight")
        date_str = request.form.get("date")
        
        # (バリデーションは省略...必要に応じて追加)

        full_datetime = f"{date_str} {datetime.now().strftime('%H:%M:%S')}"
        db.execute(
            'INSERT INTO weights (user_id, date, weight) VALUES (?, ?, ?)',
            (user_id, full_datetime, float(weight_str))
        )
        db.commit()
        flash('体重を記録しました!')
        return redirect(url_for('weight_page'))

    weight_records_asc = db.execute('SELECT date, weight FROM weights WHERE user_id = ? ORDER BY date ASC', (user_id,)).fetchall()
    records_with_diff = []
    for i, record in enumerate(weight_records_asc):
        record_dict = dict(record)
        if i > 0:
            difference = record['weight'] - weight_records_asc[i-1]['weight']
            record_dict['difference'] = difference
        else:
            record_dict['difference'] = None
        records_with_diff.append(record_dict)
    records_with_diff.reverse()

    graph_data = db.execute('SELECT STRFTIME("%Y-%m-%d", date) as day, MIN(weight) as min_weight FROM weights WHERE user_id = ? GROUP BY day ORDER BY day', (user_id,)).fetchall()
    dates = [row['day'] for row in graph_data]
    weights = [row['min_weight'] for row in graph_data]
    
    return render_template('weight.html', records=records_with_diff, dates=dates, weights=weights)

# 食事記録ページ
@app.route('/meal')
@login_required
def meal_page():
    user_id = g.user['id']
    db = get_db()
    meals = db.execute('SELECT * FROM meals WHERE user_id = ? ORDER BY date DESC, id DESC', (user_id,)).fetchall()
    return render_template('meal.html', meals=meals)

# 食事記録フォーム
@app.route('/meal_form')
@login_required
def meal_form():
    return render_template('meal_form.html')

# 食事データ追加
@app.route('/add_meal', methods=['POST'])
@login_required
def add_meal():
    user_id = g.user['id']
    # ... (フォームデータの取得とバリデーションは省略) ...
    date = request.form.get('date')
    time_slot = request.form.get('time_slot')
    content = request.form.get('content')
    ingredients = request.form.get('ingredients')
    photo = request.files.get('image')
    
    photo_path = None
    if photo and photo.filename:
        filename = secure_filename(photo.filename)
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        photo.save(photo_path)
    
    db = get_db()
    db.execute(
        'INSERT INTO meals (user_id, date, time_slot, content, ingredients, image_path) VALUES (?, ?, ?, ?, ?, ?)',
        (user_id, date, time_slot, content, ingredients, photo_path)
    )
    db.commit()
    flash('食事を記録しました！')
    return redirect(url_for('meal_page'))

# トレーニング記録ページ
@app.route('/training', methods=['GET', 'POST'])
@login_required
def training_page():
    user_id = g.user['id']
    db = get_db()
    
    if request.method == 'POST':
        # ... (フォームデータ取得とバリデーションは省略) ...
        date = request.form.get("date")
        part = request.form.get("part")
        event = request.form.get("event")

        cursor = db.execute(
            'INSERT INTO training_sessions (user_id, date, part, event) VALUES (?, ?, ?, ?)',
            (user_id, date, part, event)
        )
        db.commit()
        session_id = cursor.lastrowid

        set_number = 1
        while True:
            weight = request.form.get(f'weight_{set_number}')
            reps = request.form.get(f'reps_{set_number}')
            if weight is not None and reps is not None and weight and reps:
                db.execute('INSERT INTO training_sets (session_id, set_number, weight, reps) VALUES (?, ?, ?, ?)', (session_id, set_number, float(weight), int(reps)))
                set_number += 1
            else:
                break
        db.commit()
        flash('トレーニングを記録しました！')
        return redirect(url_for('training_page'))

    sessions = db.execute('SELECT * FROM training_sessions WHERE user_id = ? ORDER BY date DESC, id DESC', (user_id,)).fetchall()
    sessions_with_sets = []
    for session in sessions:
        session_dict = dict(session)
        sets = db.execute('SELECT * FROM training_sets WHERE session_id = ? ORDER BY set_number ASC', (session['id'],)).fetchall()
        session_dict['sets'] = sets
        sessions_with_sets.append(session_dict)
    
    return render_template('training.html', sessions=sessions_with_sets)

# --- アプリケーションの実行 ---
if __name__ == "__main__":
    app.run(debug=True)