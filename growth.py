"""90-day growth features integrated with dietapp's existing user identity."""
import calendar
import json
import math
from datetime import date, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo
from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for

growth = Blueprint('growth', __name__, url_prefix='/growth')
growth.add_app_template_filter(json.loads, 'fromjson')
CATEGORIES = [(1, '外見・体型', 4, 7), (2, '精神的な余裕', 5, 7), (3, 'コミュニケーション力', 5, 7), (4, '頼もしさ・人間性', 5, 8), (5, '継続力・自己管理', 3, 8)]
DEFAULT_HABITS = [('毎朝の身だしなみチェック', 1, '鏡の前で1分'), ('筋トレ', 1, '週3回'), ('毎日15分の自己投資', 5, '15分'), ('人との会話を意識する', 3, '1日1回'), ('毎晩3分の振り返り', 2, '3分'), ('十分な睡眠を確保する', 5, '7時間以上')]


def today():
    return datetime.now(ZoneInfo('Asia/Tokyo')).date().isoformat()


def shift(day, days):
    return (date.fromisoformat(day) + timedelta(days=days)).isoformat()


def monday(day):
    d = date.fromisoformat(day)
    return (d - timedelta(days=d.weekday())).isoformat()


def db():
    return current_app.config['GET_DB']()


def rows(sql, params=()):
    with db().cursor() as c:
        c.execute(sql, params)
        return c.fetchall()


def execute(sql, params=()):
    with db().cursor() as c:
        c.execute(sql, params)


@growth.before_request
def authenticate():
    if g.user is None:
        return redirect(url_for('login'))


def challenge():
    challenges = rows('SELECT * FROM growth_challenges WHERE user_id = %s ORDER BY created_at DESC, id DESC', (g.user['id'],))
    return challenges[0] if challenges else None


def valid_day(day, c):
    try:
        return date.fromisoformat(day).isoformat() == day and c['start_date'] <= day <= min(today(), shift(c['start_date'], 89))
    except (ValueError, TypeError):
        return False


def text(name, max_length=3000):
    value = request.form.get(name, '').strip()
    if len(value) > max_length:
        raise ValueError('入力した文章が長すぎます。')
    return value


def scheduled(h, day):
    if day < h['start_date'] or (h['end_date'] and day >= h['end_date']):
        return False
    return h['frequency'] == 'daily' or (date.fromisoformat(day).weekday() + 1) % 7 in json.loads(h['weekdays'])


def achievement(habits, logs, days):
    done_set = {(l['habit_id'], l['date']) for l in logs if l['completed']}
    planned = [(h['id'], day) for day in days for h in habits if scheduled(h, day)]
    completed = sum(p in done_set for p in planned)
    return dict(total=len(planned), completed=completed, rate=round(completed / len(planned) * 100) if planned else None)


def streak(habits, logs, day, start):
    count = 0
    current = achievement(habits, logs, [day])
    if not current['total'] or current['completed'] != current['total']:
        day = shift(day, -1)
    while day >= start:
        result = achievement(habits, logs, [day])
        if result['total'] and result['completed'] != result['total']:
            break
        if result['total']:
            count += 1
        day = shift(day, -1)
    return count


def assessments(c, day):
    existing = rows('SELECT * FROM growth_assessments WHERE challenge_id = %s AND date <= %s ORDER BY date DESC', (c['id'], day))
    return [next((a for a in existing if a['category_id'] == category_id), dict(category_id=category_id, score=score, target_score=target, action_goal='', reflection='', date=None)) | dict(name=name) for category_id, name, score, target in CATEGORIES]


def measurement_rows(c):
    imported = rows('SELECT * FROM growth_measurements WHERE challenge_id = %s ORDER BY date', (c['id'],))
    legacy = rows('SELECT date, weight FROM weights WHERE user_id = %s ORDER BY date', (g.user['id'],))
    combined = {}
    end = min(today(), shift(c['start_date'], 89))
    for r in legacy:
        day = str(r['date'])[:10]
        if c['start_date'] <= day <= end:
            combined[day] = dict(date=day, weight=float(r['weight']), waist=None)
    for r in imported:
        if c['start_date'] <= r['date'] <= end:
            combined[r['date']] = dict(r)
    return [combined[d] for d in sorted(combined)]


def weekly_summary(c, week, habits, logs, reflections):
    through = min(shift(week, 6), today(), shift(c['start_date'], 89))
    days = [shift(week, i) for i in range(7) if c['start_date'] <= shift(week, i) <= through]
    weights = [r for r in measurement_rows(c) if r['date'] in days and r['weight'] is not None]
    imported = rows('SELECT date FROM growth_workouts WHERE challenge_id = %s', (c['id'],))
    training = rows('SELECT DISTINCT date FROM training_sessions WHERE user_id = %s', (g.user['id'],))
    workout_days = {str(r['date'])[:10] for r in [*imported, *training] if str(r['date'])[:10] in days}
    return dict(**achievement(habits, logs, days), through=through, start=max(week, c['start_date']), workouts=len(workout_days), reflection_days=sum(r['date'] in days for r in reflections), weight_change=round(float(weights[-1]['weight']) - float(weights[0]['weight']), 1) if len(weights) >= 2 else None, assessments=assessments(c, through))


def radar(values, key):
    return ' '.join(f'{140 + math.cos(-math.pi / 2 + i * 2 * math.pi / 5) * 90 * a[key] / 10:.1f},{130 + math.sin(-math.pi / 2 + i * 2 * math.pi / 5) * 90 * a[key] / 10:.1f}' for i, a in enumerate(values))


def sparkline(records, key):
    points = [(r['date'], float(r[key])) for r in records if r.get(key) is not None]
    if not points:
        return None
    lo, hi = min(v for _, v in points) - 1, max(v for _, v in points) + 1
    first, last = date.fromisoformat(points[0][0]), date.fromisoformat(points[-1][0])
    span = max((last - first).days, 1)
    chart_points = [(35 + (date.fromisoformat(d) - first).days / span * 420 if len(points) > 1 else 250, 140 - (v - lo) / (hi - lo) * 110, d, v) for d, v in points]
    return dict(points=' '.join(f'{x:.1f},{y:.1f}' for x, y, _, _ in chart_points), dots=chart_points, low=round(lo, 1), high=round(hi, 1), first=points[0][0], last=points[-1][0])


@growth.get('')
@growth.get('/<tab>')
def page(tab='dashboard'):
    if tab not in {'dashboard', 'habits', 'reflection', 'assessment', 'review', 'body'}:
        abort(404)
    c = challenge()
    if c is None:
        return render_template('growth.html', challenge=None, tab=tab, today=today(), categories=CATEGORIES)
    end = shift(c['start_date'], 89)
    last = min(today(), end)
    selected = request.args.get('date', last)
    if not valid_day(selected, c):
        selected = last
    habits = rows('SELECT * FROM growth_habits WHERE challenge_id = %s ORDER BY start_date, id', (c['id'],))
    logs = rows('SELECT l.* FROM growth_habit_logs l JOIN growth_habits h ON h.id = l.habit_id WHERE h.challenge_id = %s', (c['id'],))
    reflections = rows('SELECT * FROM growth_reflections WHERE challenge_id = %s ORDER BY date DESC', (c['id'],))
    reviews = rows('SELECT * FROM growth_reviews WHERE challenge_id = %s ORDER BY week_start DESC', (c['id'],))
    week = request.args.get('week', monday(last))
    weeks = []
    d = monday(c['start_date'])
    while d <= last:
        weeks.append(d)
        d = shift(d, 7)
    if week not in weeks:
        week = weeks[-1] if weeks else monday(last)
    summary = weekly_summary(c, week, habits, logs, reflections)
    saved = next((r for r in reviews if r['week_start'] == week), None)
    saved_data = json.loads(saved['payload']) if saved else {}
    compare = next((r for r in reviews if r['week_start'] < week), None)
    comparison = json.loads(compare['payload']) if compare else None
    ratings = assessments(c, selected)
    reflection_row = next((r for r in reflections if r['date'] == selected), None)
    reflection = json.loads(reflection_row['payload']) if reflection_row else {}
    month_string = request.args.get('month', selected[:7])
    try:
        year, month = map(int, month_string.split('-'))
        date(year, month, 1)
    except (ValueError, TypeError):
        year, month = date.fromisoformat(selected).year, date.fromisoformat(selected).month
    if not c['start_date'][:7] <= f'{year:04}-{month:02}' <= last[:7]:
        year, month = date.fromisoformat(last).year, date.fromisoformat(last).month
    first = date(year, month, 1)
    previous_month = (first - timedelta(days=1)).strftime('%Y-%m')
    next_month = (first.replace(day=28) + timedelta(days=4)).strftime('%Y-%m')
    cells = [[dict(date=f'{year:04}-{month:02}-{n:02}' if n else None, day=n) for n in w] for w in calendar.Calendar(0).monthdayscalendar(year, month)]
    reflected_days = {r['date'] for r in reflections}
    measurements = measurement_rows(c)
    imported_workouts = [dict(r, data=json.loads(r['payload'])) for r in rows('SELECT * FROM growth_workouts WHERE challenge_id = %s ORDER BY date DESC', (c['id'],))]
    emotions = [dict(r, data=json.loads(r['payload'])) for r in rows('SELECT * FROM growth_emotions WHERE challenge_id=%s AND date=%s ORDER BY id', (c['id'],selected))]
    day_number = max(0, min(90, (date.fromisoformat(today()) - date.fromisoformat(c['start_date'])).days + 1))
    week_days = [shift(monday(last), i) for i in range(7) if c['start_date'] <= shift(monday(last), i) <= last]
    current_week = achievement(habits, logs, week_days)
    return render_template('growth.html', challenge=c, emotions=emotions, tab=tab, today=today(), selected=selected, end=end, last=last, day_number=day_number, time_progress=round(day_number / 90 * 100), phase=min(3, max(1, (max(day_number, 1) - 1) // 30 + 1)), habits=habits, planned=[h for h in habits if scheduled(h, selected)], logs=logs, checked={l['habit_id'] for l in logs if l['date'] == selected and l['completed']}, daily=achievement(habits, logs, [selected]), weekly=current_week, streak=streak(habits, logs, last, c['start_date']), categories=CATEGORIES, ratings=ratings, radar_score=radar(ratings, 'score'), radar_target=radar(ratings, 'target_score'), radar_grids=[radar([dict(score=n)] * 5, 'score') for n in [2,4,6,8,10]], reflection=reflection, reflections=reflections, cells=cells, reflected_days=reflected_days, month=f'{year:04}-{month:02}', previous_month=previous_month, next_month=next_month, weeks=list(reversed(weeks)), week=week, summary=summary, saved=saved_data, comparison=comparison, reviews=reviews, measurements=measurements, weight_chart=sparkline(measurements, 'weight'), waist_chart=sparkline(measurements, 'waist'), imported_workouts=imported_workouts)


@growth.post('/start')
def start():
    if challenge() is not None:
        return redirect(url_for('growth.page'))
    try:
        start_day = date.fromisoformat(request.form.get('start_date', today())).isoformat()
    except ValueError:
        flash('正しい開始日を指定してください。')
        return redirect(url_for('growth.page'))
    if start_day > today():
        flash('開始日は今日以前の日付を選んでください。')
        return redirect(url_for('growth.page'))
    c_id = str(uuid4())
    execute('INSERT INTO growth_challenges (id,user_id,start_date,created_at) VALUES (%s,%s,%s,%s)', (c_id, g.user['id'], start_day, datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()))
    for i, (name, category_id, target) in enumerate(DEFAULT_HABITS):
        execute('INSERT INTO growth_habits (id,challenge_id,name,category_id,frequency,weekdays,target,memo,start_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)', (str(uuid4()), c_id, name, category_id, 'weekly' if i == 1 else 'daily', '[1,3,5]' if i == 1 else '[]', target, '', start_day))
    for category_id, _, score, target in CATEGORIES:
        execute('INSERT INTO growth_assessments (challenge_id,category_id,date,score,target_score) VALUES (%s,%s,%s,%s,%s)', (c_id, category_id, start_day, score, target))
    db().commit()
    flash('90日間のチャレンジを開始しました。')
    return redirect(url_for('growth.page'))


@growth.post('/save')
def save():
    c = challenge()
    if c is None:
        abort(400)
    action = request.form.get('action')
    selected = request.form.get('date', today())
    redirect_tab = {'habit': 'habits', 'archive': 'habits', 'check': 'habits', 'reflection': 'reflection', 'assessment': 'assessment', 'review': 'review', 'measurement': 'body', 'emotion': 'reflection'}.get(action, 'dashboard')
    try:
        if action in {'check', 'reflection', 'assessment', 'measurement', 'emotion'} and not valid_day(selected, c):
            raise ValueError('チャレンジ期間内の過去または今日の日付を選んでください。')
        if action == 'habit':
            name, target, memo = text('name', 100), text('target', 100), text('memo')
            category_id = int(request.form.get('category_id', '0'))
            frequency = request.form.get('frequency', 'daily')
            weekdays = sorted({int(x) for x in request.form.getlist('weekdays')})
            if not name or category_id not in range(1, 6) or frequency not in {'daily', 'weekly', 'days'} or any(x not in range(7) for x in weekdays) or (frequency != 'daily' and not weekdays):
                raise ValueError('習慣名・カテゴリ・実施曜日を確認してください。')
            if frequency == 'weekly' and len(weekdays) != int(request.form.get('weekly_target', 3)):
                raise ValueError('週の目標回数と実施曜日の数を一致させてください。')
            if frequency == 'daily':
                weekdays = []
            habit_id = request.form.get('habit_id')
            start_day = max(today(), c['start_date'])
            if start_day > shift(c['start_date'], 89):
                raise ValueError('新しい習慣はチャレンジ期間中に追加してください。')
            if habit_id:
                old = rows('SELECT * FROM growth_habits WHERE id = %s AND challenge_id = %s AND end_date IS NULL', (habit_id, c['id']))
                if not old:
                    abort(404)
                old = old[0]
                if old['frequency'] == frequency and json.loads(old['weekdays']) == weekdays:
                    execute('UPDATE growth_habits SET name=%s,category_id=%s,target=%s,memo=%s WHERE id=%s', (name, category_id, target, memo, habit_id))
                else:
                    new_id = str(uuid4())
                    execute('UPDATE growth_habits SET end_date=%s WHERE id=%s', (start_day, habit_id))
                    execute('INSERT INTO growth_habits (id,challenge_id,name,category_id,frequency,weekdays,target,memo,start_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)', (new_id,c['id'],name,category_id,frequency,json.dumps(weekdays),target,memo,start_day))
                    execute('UPDATE growth_habit_logs SET habit_id=%s WHERE habit_id=%s AND date >= %s', (new_id, habit_id, start_day))
            else:
                execute('INSERT INTO growth_habits (id,challenge_id,name,category_id,frequency,weekdays,target,memo,start_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)', (str(uuid4()),c['id'],name,category_id,frequency,json.dumps(weekdays),target,memo,start_day))
        elif action == 'archive':
            execute('UPDATE growth_habits SET end_date=%s WHERE id=%s AND challenge_id=%s AND end_date IS NULL', (today(),request.form.get('habit_id'),c['id']))
        elif action == 'check':
            found = rows('SELECT * FROM growth_habits WHERE id=%s AND challenge_id=%s', (request.form.get('habit_id'),c['id']))
            if not found or not scheduled(found[0], selected):
                raise ValueError('この日に予定されている習慣を選んでください。')
            completed = 1 if request.form.get('completed') == '1' else 0
            execute('INSERT INTO growth_habit_logs (habit_id,date,completed) VALUES (%s,%s,%s) ON CONFLICT(habit_id,date) DO UPDATE SET completed=excluded.completed', (found[0]['id'],selected,completed))
        elif action == 'reflection':
            payload = {key:text(key) for key in ['good','improve','accomplished','missed','emotion']}
            payload['mode'] = 'full' if request.form.get('mode') == 'full' else 'simple'
            payload['nextActions'] = [a.strip()[:300] for a in request.form.getlist('nextActions')[:3] if a.strip()]
            score = request.form.get('satisfaction', '')
            payload['satisfaction'] = int(score) if score else None
            if score and not 1 <= payload['satisfaction'] <= 10:
                raise ValueError('満足度は1〜10で入力してください。')
            if not any(payload[k] for k in ['good','improve','accomplished','missed','emotion']) and not payload['nextActions'] and not score:
                raise ValueError('ひとことだけでも記入してください。')
            execute('INSERT INTO growth_reflections (id,challenge_id,date,payload) VALUES (%s,%s,%s,%s) ON CONFLICT(challenge_id,date) DO UPDATE SET payload=excluded.payload', (str(uuid4()),c['id'],selected,json.dumps(payload,ensure_ascii=False)))
        elif action == 'emotion':
            payload = {key:text(key) for key in ['fact','emotion','interpretation','alternative']}
            payload['action'] = text('next_action')
            if not all(payload.values()):
                raise ValueError('感情の記録をすべて記入してください。')
            execute('INSERT INTO growth_emotions (id,challenge_id,date,payload) VALUES (%s,%s,%s,%s)', (str(uuid4()),c['id'],selected,json.dumps(payload,ensure_ascii=False)))
        elif action == 'assessment':
            for category_id, _, _, _ in CATEGORIES:
                score, target = int(request.form.get(f'score_{category_id}',0)), int(request.form.get(f'target_{category_id}',0))
                if not 1 <= score <= 10 or not 1 <= target <= 10:
                    raise ValueError('自己評価・目標は1〜10で入力してください。')
                execute('INSERT INTO growth_assessments (challenge_id,category_id,date,score,target_score,action_goal,reflection) VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(challenge_id,category_id,date) DO UPDATE SET score=excluded.score,target_score=excluded.target_score,action_goal=excluded.action_goal,reflection=excluded.reflection', (c['id'],category_id,selected,score,target,text(f'goal_{category_id}'),text(f'reflection_{category_id}')))
        elif action == 'review':
            week = request.form.get('week', '')
            if monday(week) != week or week < monday(c['start_date']) or week > monday(min(today(),shift(c['start_date'],89))):
                raise ValueError('開始済みの週を選んでください。')
            notes = {key:text(key) for key in ['accomplished','improve','priority']}
            if not any(notes.values()):
                raise ValueError('レビューを1項目以上記入してください。')
            habits=rows('SELECT * FROM growth_habits WHERE challenge_id=%s',(c['id'],))
            logs=rows('SELECT l.* FROM growth_habit_logs l JOIN growth_habits h ON h.id=l.habit_id WHERE h.challenge_id=%s',(c['id'],))
            reflections=rows('SELECT * FROM growth_reflections WHERE challenge_id=%s',(c['id'],))
            notes['summary']=weekly_summary(c,week,habits,logs,reflections)
            execute('INSERT INTO growth_reviews (id,challenge_id,week_start,payload) VALUES (%s,%s,%s,%s) ON CONFLICT(challenge_id,week_start) DO UPDATE SET payload=excluded.payload',(str(uuid4()),c['id'],week,json.dumps(notes,ensure_ascii=False)))
        elif action == 'measurement':
            weight = float(request.form['weight']) if request.form.get('weight') else None
            waist = float(request.form['waist']) if request.form.get('waist') else None
            if (weight is None and waist is None) or any(v is not None and (not math.isfinite(v) or not 30 <= v <= 250) for v in [weight,waist]):
                raise ValueError('体重かウエストを30〜250の範囲で入力してください。')
            execute('INSERT INTO growth_measurements (id,challenge_id,date,weight,waist) VALUES (%s,%s,%s,%s,%s) ON CONFLICT(challenge_id,date) DO UPDATE SET weight=excluded.weight,waist=excluded.waist',(str(uuid4()),c['id'],selected,weight,waist))
            if weight is not None:
                execute('INSERT INTO weights (user_id,date,weight) VALUES (%s,%s,%s)',(g.user['id'],selected+' 12:00:00',weight))
        else:
            abort(400)
        db().commit()
        flash('保存しました。')
    except (ValueError, TypeError, KeyError):
        db().rollback()
        flash('入力内容を確認してください。日付・回数・点数・実施曜日に誤りがあるか、記入が足りない可能性があります。')
    return redirect(url_for('growth.page', tab=redirect_tab, date=selected, week=request.form.get('week',monday(today()))))
