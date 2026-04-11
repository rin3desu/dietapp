import os
import sqlite3
import click
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, g, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from google import genai

# ==========================================
# 1. アプリケーションの初期化
# ==========================================
app = Flask(__name__)
app.secret_key = 'your-very-secret-key-that-no-one-can-guess'

# Gemini APIの設定 (最新の google-genai SDK)
gemini_api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=gemini_api_key) if gemini_api_key else None

# データベースとアップロード先の設定
data_dir = os.environ.get('RENDER_DISK_MOUNT_PATH', 'instance')
app.config['DATABASE'] = os.path.join(data_dir, 'diet.db')
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# 起動時にアップロードフォルダを作成
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# ==========================================
# 2. データベース管理
# ==========================================
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

def init_db():
    db_path = app.config['DATABASE']
    db_dir = os.path.dirname(db_path)
    os.makedirs(db_dir, exist_ok=True)

    db = get_db()
    with app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

@app.cli.command('init-db')
def init_db_command():
    """データベースをクリアし、新しいテーブルを作成します。"""
    init_db()
    click.echo('データベースの初期化が完了しました。')


# ==========================================
# 3. ユーザー認証
# ==========================================
@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash('このページにアクセスするにはログインが必要です。')
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        db = get_db()
        error = None

        if not username: 
            error = 'ユーザー名は必須です。'
        elif not password: 
            error = 'パスワードは必須です。'
        elif db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone() is not None:
            error = f"ユーザー名 {username} は既に使用されています。"

        if error is None:
            db.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', 
                       (username, generate_password_hash(password)))
            db.commit()
            flash('登録が完了しました。ログインしてください。')
            return redirect(url_for('login'))
        flash(error)
    return render_template('register.html')

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

@app.route('/logout')
def logout():
    session.clear()
    flash('ログアウトしました。')
    return redirect(url_for('index'))


# ==========================================
# 4. メイン機能（ダッシュボード・各種記録）
# ==========================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/mypage')
@login_required
def mypage():
    db = get_db()
    user_id = g.user['id']
    
    # 登録されているマイジムを取得
    gyms = db.execute('SELECT * FROM gyms WHERE user_id = ?', (user_id,)).fetchall()
    
    # 最新の体重を取得
    latest_weight = db.execute(
        'SELECT weight FROM weights WHERE user_id = ? ORDER BY date DESC LIMIT 1',
        (user_id,)
    ).fetchone()
    current_weight = latest_weight['weight'] if latest_weight else '未記録'
    
    # トレーニングした日付を取得(重複なし)
    training_dates = db.execute(
        'SELECT DISTINCT date FROM training_sessions WHERE user_id = ? ORDER BY date DESC',
        (user_id,)
    ).fetchall()
    
    return render_template('mypage.html', gyms=gyms, current_weight=current_weight, training_dates=training_dates)


# --- 体重管理 ---
@app.route('/weight', methods=['GET', 'POST'])
@login_required
def weight_page():
    user_id = g.user['id']
    db = get_db()
    
    if request.method == 'POST':
        weight_str = request.form.get("weight")
        date_str = request.form.get("date")
        
        full_datetime = f"{date_str} {datetime.now().strftime('%H:%M:%S')}"
        db.execute(
            'INSERT INTO weights (user_id, date, weight) VALUES (?, ?, ?)',
            (user_id, full_datetime, float(weight_str))
        )
        db.commit()
        flash('体重を記録しました!')
        return redirect(url_for('weight_page'))

    # 前日比の計算
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

    # グラフ用データ
    graph_data = db.execute('SELECT STRFTIME("%Y-%m-%d", date) as day, MIN(weight) as min_weight FROM weights WHERE user_id = ? GROUP BY day ORDER BY day', (user_id,)).fetchall()
    dates = [row['day'] for row in graph_data]
    weights = [row['min_weight'] for row in graph_data]
    
    return render_template('weight.html', records=records_with_diff, dates=dates, weights=weights, today=datetime.now().strftime('%Y-%m-%d'))


# --- 食事管理 ---
@app.route('/meal')
@login_required
def meal_page():
    user_id = g.user['id']
    db = get_db()
    meals = db.execute('SELECT * FROM meals WHERE user_id = ? ORDER BY date DESC, id DESC', (user_id,)).fetchall()
    return render_template('meal.html', meals=meals)

@app.route('/meal_form')
@login_required
def meal_form():
    return render_template('meal_form.html')

@app.route('/add_meal', methods=['POST'])
@login_required
def add_meal():
    user_id = g.user['id']
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


# --- トレーニング管理 ---
@app.route('/training', methods=['GET', 'POST'])
@login_required
def training_page():
    db = get_db()
    user_id = g.user['id']
    today = datetime.now().strftime('%Y-%m-%d')

    # マスターデータ
    exercise_master = {
        "胸": ["ベンチプレス", "ペックフライ", "チェストプレス"],
        "背中": ["デッドリフト", "ラットプルダウン", "プーリーロー"],
        "脚": ["スクワット", "スミスマシン・バーベルスクワット", "レッグプレス"],
        "肩": ["ショルダープレス", "サイドレイズ"],
        "腕": ["アームカール", "トライセプスプレス"],
        "腹": ["クランチ", "プランク"]
    }

    # ユーザー追加のカスタム種目を合体
    customs = db.execute('SELECT muscle_group, name FROM custom_exercises WHERE user_id = ?', (user_id,)).fetchall()
    for row in customs:
        if row['muscle_group'] in exercise_master:
            if row['name'] not in exercise_master[row['muscle_group']]:
                exercise_master[row['muscle_group']].append(row['name'])

    if request.method == 'POST':
        # 新しいカスタム種目の追加
        if request.form.get('new_exercise_name'):
            new_name = request.form.get('new_exercise_name')
            part = request.form.get('muscle_group')
            db.execute('INSERT INTO custom_exercises (user_id, muscle_group, name) VALUES (?, ?, ?)', (user_id, part, new_name))
            db.commit()
            flash(f"「{new_name}」を新しく追加しました！")
            return redirect(url_for('training_page'))

        # トレーニングの記録
        else:
            date = request.form.get('date')
            part = request.form.get('muscle_group')
            event = request.form.get('exercise_name')
            weights = request.form.getlist('weights[]')
            reps = request.form.getlist('reps[]')

            if part and event:
                cursor = db.execute(
                    'INSERT INTO training_sessions (user_id, date, part, event) VALUES (?, ?, ?, ?)',
                    (user_id, date, part, event)
                )
                session_id = cursor.lastrowid
                
                for w, r in zip(weights, reps):
                    if w and r:
                        db.execute(
                            'INSERT INTO training_sets (session_id, weight, reps) VALUES (?, ?, ?)',
                            (session_id, float(w), int(r))
                        )
                db.commit()
                flash("トレーニングを記録しました！")
            return redirect(url_for('training_page'))

    # GET時のデータ取得
    stats = db.execute('''
        SELECT COUNT(DISTINCT event) as events, COUNT(*) as sets, SUM(reps) as reps 
        FROM training_sessions s JOIN training_sets t ON s.id = t.session_id 
        WHERE s.user_id = ? AND s.date = ?''', (user_id, today)
    ).fetchone()

    raw_sessions = db.execute('SELECT * FROM training_sessions WHERE user_id = ? ORDER BY date DESC', (user_id,)).fetchall()
    sessions = []
    for s in raw_sessions:
        sets = db.execute('SELECT weight, reps FROM training_sets WHERE session_id = ?', (s['id'],)).fetchall()
        sessions.append({
            'date': s['date'],
            'muscle_group': s['part'],
            'exercise_name': s['event'],
            'sets': sets
        })

    return render_template('training.html', master=exercise_master, stats=stats, today=today, sessions=sessions)


# ==========================================
# 5. マイジム・マシン管理
# ==========================================
@app.route('/gym_register', methods=['GET', 'POST'])
@login_required
def gym_register():
    db = get_db()
    user_id = g.user['id']

    if request.method == 'POST':
        gym_name = request.form.get('gym_name')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')

        if gym_name and latitude and longitude:
            db.execute(
                'INSERT INTO gyms (user_id, name, latitude, longitude) VALUES (?, ?, ?, ?)',
                (user_id, gym_name, latitude, longitude)
            )
            db.commit()
            flash(f"「{gym_name}」をマイジムに登録しました！")
            return redirect(url_for('gym_register'))
        else:
            flash("正しく位置情報が取得できませんでした。もう一度お試しください。")

    gyms = db.execute('SELECT * FROM gyms WHERE user_id = ? ORDER BY id DESC', (user_id,)).fetchall()
    return render_template('gym_register.html', gyms=gyms)


@app.route('/gym/<int:gym_id>')
@login_required
def gym_detail(gym_id):
    db = get_db()
    user_id = g.user['id']

    gym = db.execute('SELECT * FROM gyms WHERE id = ? AND user_id = ?', (gym_id, user_id)).fetchone()
    
    if gym is None:
        flash('指定されたジムが見つからないか、アクセス権がありません。')
        return redirect(url_for('mypage'))

    machines = db.execute('SELECT * FROM machines WHERE gym_id = ? ORDER BY target_muscle, id DESC', (gym_id,)).fetchall()
    return render_template('gym_detail.html', gym=gym, machines=machines)


@app.route('/gym/<int:gym_id>/add_machine', methods=['POST'])
@login_required
def add_machine(gym_id):
    db = get_db()
    user_id = g.user['id']

    machine_name = request.form.get('machine_name')
    target_muscle = request.form.get('target_muscle')

    gym = db.execute('SELECT id FROM gyms WHERE id = ? AND user_id = ?', (gym_id, user_id)).fetchone()

    if gym and machine_name and target_muscle:
        db.execute('INSERT INTO machines (gym_id, name, target_muscle) VALUES (?, ?, ?)',
                   (gym_id, machine_name, target_muscle))
        db.commit()
        flash(f'「{machine_name}」を登録しました！')
    else:
        flash('マシン名と対象部位を選択・入力してください。')

    return redirect(url_for('gym_detail', gym_id=gym_id))


@app.route('/delete_gym/<int:gym_id>', methods=['POST'])
@login_required
def delete_gym(gym_id):
    db = get_db()
    user_id = g.user['id']

    gym = db.execute('SELECT * FROM gyms WHERE id = ? AND user_id = ?', (gym_id, user_id)).fetchone()
    
    if gym:
        db.execute('DELETE FROM machines WHERE gym_id = ?', (gym_id,))
        db.execute('DELETE FROM gyms WHERE id = ?', (gym_id,))
        db.commit()
        flash(f'「{gym["name"]}」を削除しました。')
    else:
        flash('削除に失敗しました。')

    return redirect(url_for('mypage'))


# ==========================================
# 6. AIメニュー提案機能
# ==========================================
@app.route('/recommend', methods=['GET', 'POST'])
@login_required
def recommend_page():
    db = get_db()
    user_id = g.user['id']
    
    gyms = db.execute('SELECT * FROM gyms WHERE user_id = ?', (user_id,)).fetchall()
    recommendation = None

    if request.method == 'POST':
        gym_id = request.form.get('gym_id')
        target_muscle = request.form.get('target_muscle')
        time_minutes = request.form.get('time_minutes')

        machines = db.execute(
            'SELECT name FROM machines WHERE gym_id = ? AND target_muscle = ?',
            (gym_id, target_muscle)
        ).fetchall()

        if not machines:
            flash(f'そのジムには「{target_muscle}」用のマシンが登録されていません。')
        elif not client:
            flash('APIキーが設定されていないため、AI機能を利用できません。')
        else:
            machine_names = ", ".join([m['name'] for m in machines])

            prompt = f"""
            あなたはプロのトレーナーとして、簡潔で実用的なメニューのみを作成してください。
            余計な挨拶、励まし、導入文は一切不要です。以下の【形式】を厳守してください。

            【条件】
            - 対象部位: {target_muscle}
            - 所要時間: {time_minutes}分
            - 利用可能なマシン: {machine_names}

            【形式】
            1. [マシン名] [回数]回[セット数]セット インターバル[分]分 想定[分]分
            2. ...（マシンの数に合わせて作成）

            [マシン名]のアドバイス：
            [1行で簡潔に意識するポイントを記述]
            """

            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash', 
                    contents=prompt
                )
                recommendation = response.text
            except Exception as e:
                flash(f"AIの生成中にエラーが発生しました: {e}")

    return render_template('recommend.html', gyms=gyms, recommendation=recommendation)

# ==========================================
# アプリケーションの実行
# ==========================================
if __name__ == "__main__":
    app.run(debug=True)