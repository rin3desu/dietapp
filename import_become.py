"""Explicit account-scoped, read-only and idempotent BECOME import."""
import json
import sqlite3
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5
from flask import current_app


def import_records(source, username):
    path = Path(source).resolve(strict=True)
    destination = current_app.config.get('SQLITE_PATH')
    if not current_app.config.get('DATABASE_URL') and destination and path == Path(destination).resolve():
        raise ValueError('Source and destination must differ')
    old = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    old.row_factory = sqlite3.Row
    db = current_app.config['GET_DB']()
    tables = {r[0] for r in old.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    def records(table):
        if table not in tables:
            return []
        return [dict(r) for r in old.execute('SELECT * FROM "' + table + '"')]

    def insert(sql, params):
        with db.cursor() as cursor:
            cursor.execute(sql, params)

    try:
        with db.cursor() as cursor:
            cursor.execute('SELECT id FROM users WHERE username=%s', (username,))
            user = cursor.fetchone()
        if user is None:
            raise ValueError('Create the destination account before importing')
        uid = user['id']
        key = lambda kind, ident: str(uuid5(NAMESPACE_URL, f'stoiq/become/{uid}/{kind}/{ident}'))
        count = 0
        for c in records('Challenge'):
            cid = key('challenge', c['id'])
            with db.cursor() as cursor:
                cursor.execute('SELECT id FROM growth_challenges WHERE id=%s', (cid,))
                if cursor.fetchone():
                    continue
            insert('INSERT INTO growth_challenges(id,user_id,start_date,created_at) VALUES (%s,%s,%s,%s)', (cid,uid,c['startDate'],str(c['createdAt'])))
            habits = [r for r in records('Habit') if r['challengeId']==c['id']]
            for h in habits:
                hid = key('habit',h['id'])
                insert('INSERT INTO growth_habits(id,challenge_id,name,category_id,frequency,weekdays,target,memo,start_date,end_date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', (hid,cid,h['name'],h['categoryId'],h['frequency'],h['weekdays'],h['target'],h['memo'],h['startDate'],h['endDate']))
                for log in records('HabitLog'):
                    if log['habitId']==h['id']:
                        insert('INSERT INTO growth_habit_logs(habit_id,date,completed,memo) VALUES (%s,%s,%s,%s)',(hid,log['date'],int(log['completed']),log.get('memo','')))
            for a in records('CategoryAssessment'):
                if a['challengeId']==c['id']:
                    insert('INSERT INTO growth_assessments(challenge_id,category_id,date,score,target_score,action_goal,reflection) VALUES (%s,%s,%s,%s,%s,%s,%s)',(cid,a['categoryId'],a['date'],a['score'],a['targetScore'],a['actionGoal'],a['reflection']))
            for table, target in [('DailyReflection','growth_reflections'),('EmotionLog','growth_emotions'),('WorkoutSession','growth_workouts')]:
                for r in records(table):
                    if r['challengeId']!=c['id']:
                        continue
                    payload = dict(r)
                    if table=='DailyReflection':
                        payload['nextActions']=json.loads(r['nextActions'])
                    if table=='WorkoutSession':
                        payload['sets']=[s for s in records('WorkoutSet') if s['sessionId']==r['id']]
                    insert(f'INSERT INTO {target}(id,challenge_id,date,payload) VALUES (%s,%s,%s,%s)',(key(table,r['id']),cid,r['date'],json.dumps(payload,ensure_ascii=False)))
            for r in records('BodyMeasurement'):
                if r['challengeId']==c['id']:
                    insert('INSERT INTO growth_measurements(id,challenge_id,date,weight,waist) VALUES (%s,%s,%s,%s,%s)',(key('measurement',r['id']),cid,r['date'],r['weight'],r['waist']))
            for r in records('WeeklyReview'):
                if r['challengeId']==c['id']:
                    payload=dict(accomplished=r['accomplished'],improve=r['improve'],priority=r['priority'],legacy_snapshot=json.loads(r['snapshot']))
                    insert('INSERT INTO growth_reviews(id,challenge_id,week_start,payload) VALUES (%s,%s,%s,%s)',(key('review',r['id']),cid,r['weekStart'],json.dumps(payload,ensure_ascii=False)))
            count+=1
        profiles=records('UserSettings')
        if profiles:
            insert('INSERT INTO growth_profiles(user_id,payload) VALUES (%s,%s) ON CONFLICT(user_id) DO NOTHING',(uid,json.dumps(profiles[0],ensure_ascii=False)))
        db.commit()
        return count
    except Exception:
        db.rollback()
        raise
    finally:
        old.close()
