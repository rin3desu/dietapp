import os
import sqlite3
import click
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, g, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from google import genai


# --- アプリケーションの初期化 ---
app = Flask(__name__)

# 【修正点】secret_key を設定。これはflashやsession機能に必須です。
app.secret_key = 'your-very-secret-key-that-no-one-can-guess'
# Gemini APIの設定
gemini_api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=gemini_api_key) if gemini_api_key else None

# Renderの環境変数から永続ディスクのパスを取得し、なければローカルの'instance'フォルダを使う
data_dir = os.environ.get('RENDER_DISK_MOUNT_PATH', 'instance')
app.config['DATABASE'] = os.path.join(data_dir, 'diet.db')
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

# 【修正点】重複していたinit_db関数を1つに統合
def init_db():
    # データベースのディレクトリが存在することを確実にする
    db_path = app.config['DATABASE']
    db_dir = os.path.dirname(db_path)
    os.makedirs(db_dir, exist_ok=True)

    db = get_db()
    with app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

# 【修正点】'init-db' コマンドをFlask CLIに登録する
@app.cli.command('init-db')
def init_db_command():
    """データベースをクリアし、新しいテーブルを作成します。"""
    init_db()
    click.echo('データベースの初期化が完了しました。')


# --- ユーザー認証 ---

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


# --- メイン機能 ---

@app.route('/')
def index():
    return render_template('index.html')

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

@app.route('/training', methods=['GET', 'POST'])
@login_required
def training_page():
    user_id = g.user['id']
    db = get_db()
    
    if request.method == 'POST':
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

@app.route('/mypage')
@login_required
def mypage():
    db = get_db()
    user_id = g.user['id']
    
    # 登録されているマイジムを取得
    gyms = db.execute('SELECT * FROM gyms WHERE user_id = ?', (user_id,)).fetchall()
    
    #　最新の体重を取得
    latest_weight = db.execute(
        'SELECT weight FROM weights WHERE user_id = ? ORDER BY date DESC LIMIT 1',
        (user_id,)
    ).fetchone()
    
    #記録がない場合は「未記録」と表示する
    current_weight = latest_weight['weight'] if latest_weight else '未記録'
    
    #トレーニングした日付を取得(重複なし)
    training_dates = db.execute(
        'SELECT DISTINCT date FROM training_sessions WHERE user_id = ? ORDER BY date DESC',
        (user_id,)
    ).fetchall()
    
    return render_template('mypage.html', gyms=gyms, current_weight=current_weight, training_dates=training_dates)


@app.route('/gym_register', methods=['GET', 'POST'])
def gym_register():
    # ログインしていない場合はログイン画面へ
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_id = session['user_id']
        gym_name = request.form.get('gym_name')
        lat = request.form.get('latitude')
        lng = request.form.get('longitude')

        # ピンが置かれていない（緯度経度がない）場合はエラー
        if not lat or not lng:
            flash('地図上でジムの場所をクリックしてピンを立ててください。')
            return redirect(url_for('gym_register'))

        db = get_db()
        
        # 【重要】すでに登録されているマイジムの数をカウントする
        count = db.execute('SELECT COUNT(*) FROM gyms WHERE user_id = ?', (user_id,)).fetchone()[0]
        
        if count >= 2:
            flash('マイジムは2件までしか登録できません。')
            return redirect(url_for('gym_register'))

        # 2件未満ならデータベースに保存
        db.execute('INSERT INTO gyms (user_id, name, latitude, longitude) VALUES (?, ?, ?, ?)',
                   (user_id, gym_name, lat, lng))
        db.commit()
        
        flash(f'「{gym_name}」をマイジムに登録しました！')
        # 登録後はマイページなどに戻る（いったんトップページにしています）
        return redirect(url_for('index'))

    # GETメソッドの場合は単に画面を表示
    return render_template('gym_register.html')

@app.route('/gym/<int:gym_id>', methods=['GET', 'POST'])
@login_required
def gym_detail(gym_id):
    db = get_db()
    user_id = g.user['id']

    # 1. 指定されたジムが、ログイン中のユーザーのものか確認する
    gym = db.execute('SELECT * FROM gyms WHERE id = ? AND user_id = ?', (gym_id, user_id)).fetchone()
    
    if gym is None:
        flash('指定されたジムが見つからないか、アクセス権がありません。')
        return redirect(url_for('mypage'))

    # 2. マシンを登録する処理（POSTリクエスト時）
    if request.method == 'POST':
        machine_name = request.form.get('machine_name')
        target_muscle = request.form.get('target_muscle')

        if not machine_name or not target_muscle:
            flash('マシン名と対象部位を選択・入力してください。')
        else:
            db.execute('INSERT INTO machines (gym_id, name, target_muscle) VALUES (?, ?, ?)',
                       (gym_id, machine_name, target_muscle))
            db.commit()
            flash(f'「{machine_name}」を登録しました！')
            return redirect(url_for('gym_detail', gym_id=gym_id))

    # 3. このジムに登録されているマシンの一覧を取得する
    machines = db.execute('SELECT * FROM machines WHERE gym_id = ? ORDER BY target_muscle, id DESC', (gym_id,)).fetchall()

    return render_template('gym_detail.html', gym=gym, machines=machines)

@app.route('/delete_gym/<int:gym_id>', methods=['POST'])
@login_required
def delete_gym(gym_id):
    db = get_db()
    user_id = g.user['id']

    # 1. 削除対象のジムが、ログイン中のユーザーのものか確認
    gym = db.execute('SELECT * FROM gyms WHERE id = ? AND user_id = ?', (gym_id, user_id)).fetchone()
    
    if gym:
        # 2. そのジムに紐付いているマシンを先に削除
        db.execute('DELETE FROM machines WHERE gym_id = ?', (gym_id,))
        
        # 3. ジム自体を削除
        db.execute('DELETE FROM gyms WHERE id = ?', (gym_id,))
        db.commit()
        flash(f'「{gym["name"]}」を削除しました。')
    else:
        flash('削除に失敗しました。アクセス権がないか、既に削除されています。')

    return redirect(url_for('mypage'))

@app.route('/recommend', methods=['GET', 'POST'])
@login_required
def recommend_page():
    db = get_db()
    user_id = g.user['id']
    
    # 選択肢用のジムリスト取得
    gyms = db.execute('SELECT * FROM gyms WHERE user_id = ?', (user_id,)).fetchall()
    recommendation = None

    if request.method == 'POST':
        gym_id = request.form.get('gym_id')
        target_muscle = request.form.get('target_muscle')
        time_minutes = request.form.get('time_minutes')

        # デバッグ用プリント
        print(f"DEBUG: gym_id={gym_id}, muscle={target_muscle}, time={time_minutes}")

        machines = db.execute(
            'SELECT name FROM machines WHERE gym_id = ? AND target_muscle = ?',
            (gym_id, target_muscle)
        ).fetchall()

        # マシンが何件見つかったか表示
        print(f"DEBUG: 見つかったマシンの数: {len(machines)}")

        if not machines:
            flash(f'そのジムには「{target_muscle}」用のマシンが登録されていません。')
        elif not client:
            print("DEBUG: APIキーが読み込めていません(client is None)")
            flash('APIキーが設定されていないため、AI機能を利用できません。')
        else:
            machine_names = ", ".join([m['name'] for m in machines])
            print(f"DEBUG: AIに送るマシンリスト: {machine_names}")

            # --- 【ここから修正：prompt の中身を定義する】 ---
            prompt = f"""
            あなたはプロのトレーナーとして、簡潔で実用的なメニューのみを作成してください。
            余計な挨拶、励まし、導入文は一切不要です。以下の【形式】を厳守してください。

            【条件】
            - 対象部位: {target_muscle}
            - 所要時間: {time_minutes}分
            - 利用可能なマシン: {machine_names}

            【形式】
            今回のトレーニングメニュー
            1. [マシン名] [回数]回[セット数]セット インターバル[分]分 想定[分]分
            2. ...（マシンの数に合わせて作成）

            [マシン名]のアドバイス：
            [1行で簡潔に意識するポイントを記述]
            
            
            出力は、上記の形式に沿ったテキストのみとしてください。解説や挨拶は含めないでください。
            """
            # --- 【ここまで】 ---

            try:
                print("DEBUG: AIにリクエスト送信中...")
                response = client.models.generate_content(
                    # 'gemini-2.0-flash' から以下のいずれかに変更
                    model='gemini-2.5-flash', 
                    # もしくは model='gemini-flash-latest'
                    contents=prompt
                )
                recommendation = response.text
                print("DEBUG: AIから回答を受信しました！")
            except Exception as e:
                print(f"DEBUG: AIエラー発生: {e}")
                flash(f"AIの生成中にエラーが発生しました: {e}")

    return render_template('recommend.html', gyms=gyms, recommendation=recommendation)

# --- アプリケーションの実行 ---
if __name__ == "__main__":
    app.run(debug=False)