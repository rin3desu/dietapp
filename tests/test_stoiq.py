import hashlib
import io
import json
import os
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import pytest
from PIL import Image
from app import app, get_db
from stoic_db import migrate
from growth import today, shift, monday, achievement, streak
from recipes_data import RECIPES


@pytest.fixture
def configured(tmp_path):
    pg_url=os.getenv('STOIQ_TEST_POSTGRES_URL')
    control=None
    if pg_url:
        import psycopg2
        from urllib.parse import urlsplit
        parsed=urlsplit(pg_url)
        if parsed.hostname!='127.0.0.1' or parsed.port!=55439 or parsed.username!='stoiq_qa':
            raise RuntimeError('PostgreSQL tests require the dedicated local test cluster')
        control=psycopg2.connect(pg_url)
        control.autocommit=True
        schema='qa_'+uuid4().hex
        with control.cursor() as cursor:
            cursor.execute('CREATE SCHEMA '+schema)
        pg_url+='?options=-csearch_path%3D'+schema
    app.config.update(TESTING=True, SECRET_KEY='tests-only', DATABASE_URL=pg_url,
        SQLITE_PATH=str(tmp_path/'test.db'), RECIPE_PHOTO_FOLDER=str(tmp_path/'photos'),
        GEMINI_API_KEY=None, FOOD_AI_CLIENT=None, AI_DAILY_LIMIT=10, SESSION_COOKIE_SECURE=False)
    migrate(app.config)
    with app.app_context():
        with get_db().cursor() as c:
            c.execute("INSERT INTO users(username,password_hash) VALUES (%s,%s)",('owner','unused'))
            c.execute("INSERT INTO users(username,password_hash) VALUES (%s,%s)",('other','unused'))
        get_db().commit()
    yield app
    if control:
        with control.cursor() as cursor:
            cursor.execute('DROP SCHEMA '+schema+' CASCADE')
        control.close()


def client(uid=1):
    c=app.test_client()
    with c.session_transaction() as s:
        s['_csrf']='test-token'
        if uid: s['user_id']=uid
    return c


def post(c,url,data=None,**kwargs):
    if 'json' in kwargs:
        return c.post(url,headers={'X-CSRF-Token':'test-token'},**kwargs)
    return c.post(url,data={'csrf_token':'test-token',**(data or {})},**kwargs)


def query(sql, params=()):
    with app.app_context():
        with get_db().cursor() as c:
            c.execute(sql,params)
            return c.fetchall()


def start(c):
    assert post(c,'/growth/start',{'start_date':shift(today(),-10)}).status_code==302


def draft(c):
    result=post(c,'/food/suggest',json=dict(ingredients='卵、豆腐',avoid='',goal='muscle',minutes=20,servings=1,consent=True))
    assert result.status_code==200, result.data
    return result.json['recipes'][0]['id']


class FakeAI:
    def __init__(self, invalid=False):
        self.models=self
        self.calls=[]
        self.invalid=invalid
    def generate_content(self,**kwargs):
        self.calls.append(kwargs)
        recipe=dict(title='豆腐と卵の炒め物',subtitle='食材を使い切る',goal='muscle',minutes=15,servings=1,protein_source='豆腐・卵',ingredients=[dict(name='豆腐',amount='150g'),dict(name='卵',amount='1個')],steps=['豆腐を水切りする。','卵と豆腐を中心まで十分加熱する。'],tip='野菜も添える。',allergy=['卵','大豆'])
        if self.invalid: recipe['photo_url']='https://example.com/ai.jpg'
        return SimpleNamespace(text=json.dumps(dict(recipes=[recipe]),ensure_ascii=False))


def test_public_catalogue_and_alias_search(configured):
    c=client(None)
    assert c.get('/').status_code==200
    page=c.get('/food').get_data(as_text=True)
    assert page.count('<article class="recipe-card">')==5
    assert 'STOIQ' in page and '/growth' in page
    for term,ident in [('鶏胸肉','chicken-broccoli'),('玉子','tuna-egg-salad'),('とうふ','crispy-tofu')]:
        body=c.get('/food',query_string={'q':term}).get_data(as_text=True)
        assert ident in body and body.count('<article class="recipe-card">')==1
    empty=c.get('/food?q=鶏むね肉+豆腐').get_data(as_text=True)
    assert 'ぴったりのレシピは' in empty
    assert c.get('/food?goal=diet').get_data(as_text=True).count('<article class="recipe-card">')==2
    for r in RECIPES:
        assert c.get('/food/recipes/'+r['id']).status_code==200
        image=c.get('/static/images/recipes/'+r['photo'])
        assert image.status_code==200 and image.mimetype=='image/jpeg'
        Image.open(io.BytesIO(image.data)).verify()


def test_auth_csrf_and_legacy_pages(configured):
    guest=client(None)
    assert guest.get('/growth').status_code==302
    assert guest.get('/food/mine').status_code==302
    assert guest.post('/growth/start').status_code==403
    assert post(guest,'/food/suggest',json={}).status_code==401
    c=client()
    for url in ['/mypage','/weight','/meal','/meal_form','/training','/gym_register','/recommend','/food/mine','/growth']:
        assert c.get(url).status_code==200,url
    result=c.post('/growth/start',data={'csrf_token':'test-token'},headers={'Origin':'https://evil.invalid'})
    assert result.status_code==403
    assert c.get('/growth').headers['Cache-Control']=='private, no-store'


def test_existing_training_weight_and_meals(configured):
    c=client()
    assert post(c,'/weight',{'date':today(),'weight':'72.4'}).status_code==302
    assert post(c,'/training',{'date':today(),'muscle_group':'胸','exercise_name':'ベンチプレス','weights[]':['50','55'],'reps[]':['10','8']}).status_code==302
    assert len(query('SELECT * FROM training_sets'))==2
    assert post(c,'/add_meal',{'date':today(),'time_slot':'昼','content':'豆腐','ingredients':'豆腐'}).status_code==302
    for url in ['/weight','/training','/meal','/mypage']:
        assert c.get(url).status_code==200


def test_postgres_existing_timestamp_columns(configured):
    if not app.config.get('DATABASE_URL'):
        pytest.skip('PostgreSQL-specific compatibility check')
    with app.app_context():
        with get_db().cursor() as cursor:
            cursor.execute('ALTER TABLE weights ALTER COLUMN date TYPE TIMESTAMP USING date::timestamp')
            cursor.execute('ALTER TABLE training_sessions ALTER COLUMN date TYPE DATE USING date::date')
        get_db().commit()
    c=client();start(c)
    post(c,'/weight',{'date':today(),'weight':'72.4'})
    post(c,'/training',{'date':today(),'muscle_group':'胸','exercise_name':'ベンチプレス','weights[]':['50'],'reps[]':['10']})
    for route in ['/weight','/training','/growth/body','/growth/review']:
        assert c.get(route).status_code==200,route


def test_gym_owner_isolation(configured):
    with app.app_context():
        with get_db().cursor() as cursor:
            cursor.execute('INSERT INTO gyms(user_id,name) VALUES (%s,%s)',(2,'private gym'))
            cursor.execute('INSERT INTO machines(gym_id,name,target_muscle) VALUES (1,%s,%s)',('secret machine','胸'))
        get_db().commit()
    c=client()
    response=post(c,'/recommend',{'gym_id':'1','target_muscle':'胸','time_minutes':'20'})
    assert response.status_code==200 and b'secret machine' not in response.data
    assert c.get('/gym/1').status_code in (302,404)


def test_ai_missing_key_and_consent(configured):
    c=client()
    payload=dict(ingredients='豆腐',goal='muscle',minutes=20,servings=1,consent=True)
    assert post(c,'/food/suggest',json=payload).status_code==503
    payload['consent']=False
    assert post(c,'/food/suggest',json=payload).status_code==400
    assert query('SELECT * FROM stoiq_recipes')==[]
    assert post(c,'/food/suggest',json=['invalid']).status_code==400


def test_ai_allowlist_private_publish_and_photo(configured):
    fake=FakeAI();app.config['FOOD_AI_CLIENT']=fake
    c=client();start(c)
    post(c,'/growth/save',{'action':'reflection','date':today(),'good':'PRIVATE_DIARY'})
    rid=draft(c)
    sent=json.loads(fake.calls[0]['contents'])
    assert set(sent)=={'ingredients','purpose','excluded_ingredients','time_minutes','servings'}
    assert 'PRIVATE_DIARY' not in fake.calls[0]['contents']
    other=client(2);guest=client(None)
    assert c.get('/food/recipes/'+rid).status_code==200
    assert other.get('/food/recipes/'+rid).status_code==404
    assert guest.get('/food/recipes/'+rid).status_code==404
    assert post(other,f'/food/recipes/{rid}/publish',{'visibility':'publish','confirm_publish':'yes'}).status_code==404
    post(c,f'/food/recipes/{rid}/publish',{'visibility':'publish'})
    assert guest.get('/food/recipes/'+rid).status_code==404
    image=io.BytesIO();Image.new('RGB',(60,40),'green').save(image,'JPEG');image.seek(0)
    post(c,f'/food/recipes/{rid}/photo',{'real_photo_permission':'yes','photo':(image,'photo.jpg')},content_type='multipart/form-data')
    assert c.get(f'/food/recipes/{rid}/image').status_code==200
    assert other.get(f'/food/recipes/{rid}/image').status_code==404
    post(c,f'/food/recipes/{rid}/publish',{'visibility':'publish','confirm_publish':'yes'})
    assert guest.get('/food/recipes/'+rid).status_code==200
    assert guest.get(f'/food/recipes/{rid}/image').status_code==200
    assert rid in guest.get('/food').get_data(as_text=True)
    post(c,f'/food/recipes/{rid}/publish',{'visibility':'private'})
    assert guest.get('/food/recipes/'+rid).status_code==404


def test_ai_invalid_schema_and_rate_limit(configured):
    fake=FakeAI(invalid=True);app.config['FOOD_AI_CLIENT']=fake
    c=client();payload=dict(ingredients='豆腐',goal='muscle',minutes=20,servings=1,consent=True)
    assert post(c,'/food/suggest',json=payload).status_code==502
    assert query('SELECT * FROM stoiq_recipes')==[]
    app.config.update(FOOD_AI_CLIENT=FakeAI(),AI_DAILY_LIMIT=1)
    assert post(c,'/food/suggest',json=payload).status_code==429


def test_ai_exclusion_mismatch_and_invalid_photo(configured):
    fake=FakeAI();app.config['FOOD_AI_CLIENT']=fake
    c=client()
    payload=dict(ingredients='豆腐',avoid='玉子',goal='muscle',minutes=20,servings=1,consent=True)
    assert post(c,'/food/suggest',json=payload).status_code==502
    assert query('SELECT * FROM stoiq_recipes')==[]
    rid=draft(c)
    post(c,f'/food/recipes/{rid}/photo',{'real_photo_permission':'yes','photo':(io.BytesIO(b'<svg onload="alert(1)"/>'),'evil.jpg')},content_type='multipart/form-data')
    assert c.get(f'/food/recipes/{rid}/image').status_code==404


def test_habit_schedule_version_and_emotion(configured):
    c=client();start(c)
    h=query("SELECT * FROM growth_habits WHERE frequency='daily'")[0]
    yesterday=shift(today(),-1)
    post(c,'/growth/save',{'action':'check','date':yesterday,'habit_id':h['id'],'completed':'1'})
    post(c,'/growth/save',{'action':'habit','habit_id':h['id'],'name':h['name'],'category_id':'1','frequency':'days','weekdays':['1','3'],'target':'10分'})
    old=query('SELECT * FROM growth_habits WHERE id=%s',(h['id'],))[0]
    assert old['end_date']==today()
    assert query('SELECT * FROM growth_habit_logs WHERE habit_id=%s',(h['id'],))[0]['date']==yesterday
    post(c,'/growth/save',{'action':'emotion','date':today(),'fact':'出来事','emotion':'気持ち','interpretation':'解釈','alternative':'別の見方','next_action':'次の行動'})
    assert len(query('SELECT * FROM growth_emotions'))==1
    assert '出来事' in c.get('/growth/reflection').get_data(as_text=True)


def test_growth_pages_records_and_ownership(configured):
    c=client();start(c)
    assert len(query('SELECT * FROM growth_habits'))==6
    for tab in ['dashboard','habits','reflection','assessment','review','body']:
        assert c.get('/growth/'+tab).status_code==200,tab
    h=query("SELECT * FROM growth_habits WHERE frequency='daily'")[0]
    post(c,'/growth/save',{'action':'check','date':today(),'habit_id':h['id'],'completed':'1'})
    assert query('SELECT * FROM growth_habit_logs')[0]['completed']==1
    post(c,'/growth/save',{'action':'reflection','date':today(),'good':'<script>private</script>','nextActions':['歩く','読む']})
    body=c.get('/growth/reflection').get_data(as_text=True)
    assert '&lt;script&gt;private&lt;/script&gt;' in body
    post(c,'/growth/save',{'action':'measurement','date':today(),'weight':'72.4','waist':'80'})
    assert query('SELECT weight FROM weights')[0]['weight']==72.4
    assert c.get('/growth/body').status_code==200
    other=client(2);start(other)
    assert 'private' not in other.get('/growth/reflection').get_data(as_text=True)
    post(other,'/growth/save',{'action':'check','date':today(),'habit_id':h['id'],'completed':'0'})
    assert query('SELECT * FROM growth_habit_logs')[0]['completed']==1
    before=len(query('SELECT * FROM growth_reflections'))
    post(c,'/growth/save',{'action':'reflection','date':shift(today(),1),'good':'future'})
    assert len(query('SELECT * FROM growth_reflections'))==before


def test_assessment_rollback_and_weekly_snapshot(configured):
    c=client();start(c)
    form={'action':'assessment','date':today()}
    for i in range(1,6):form.update({f'score_{i}':'7',f'target_{i}':'9'})
    form['score_5']='99'
    post(c,'/growth/save',form)
    assert query('SELECT * FROM growth_assessments WHERE date=%s',(today(),))==[]
    form['score_5']='7';post(c,'/growth/save',form)
    assert len(query('SELECT * FROM growth_assessments WHERE date=%s',(today(),)))==5
    week=monday(today())
    post(c,'/growth/save',{'action':'review','week':week,'accomplished':'続けられた'})
    frozen=query('SELECT payload FROM growth_reviews')[0]['payload']
    post(c,'/growth/save',{'action':'reflection','date':today(),'good':'あとから記録'})
    assert query('SELECT payload FROM growth_reviews')[0]['payload']==frozen
    assert c.get('/growth/review').status_code==200


def test_schedule_denominator_and_streak():
    h=dict(id='h',start_date='2026-11-01',end_date=None,frequency='days',weekdays='[1,3,5]')
    assert achievement([h],[],['2026-11-08'])['rate'] is None
    logs=[dict(habit_id='h',date='2026-11-06',completed=1)]
    assert streak([h],logs,'2026-11-09','2026-11-01')==1
    assert achievement([h],logs,['2026-11-06','2026-11-07','2026-11-08'])['rate']==100


def test_persistent_session_key_and_startup_hook(configured,tmp_path,monkeypatch):
    from flask import Flask
    from security import configure_app
    import runpy
    monkeypatch.setenv('RENDER','true')
    monkeypatch.setenv('DATABASE_URL','postgresql://unused-test-only')
    monkeypatch.delenv('SECRET_KEY',raising=False)
    key_file=tmp_path/'persistent'/'session-key'
    monkeypatch.setenv('SESSION_KEY_FILE',str(key_file))
    first=Flask('first');configure_app(first)
    second=Flask('second');configure_app(second)
    assert first.secret_key==second.secret_key and len(first.secret_key)>=64
    assert first.config['SESSION_COOKIE_SECURE'] is True
    before=len(query('SELECT * FROM users'))
    runpy.run_path(str(Path(__file__).parents[1]/'gunicorn.conf.py'))['on_starting'](None)
    assert len(query('SELECT * FROM users'))==before


def test_non_destructive_migrations_and_import(configured,tmp_path):
    from import_become import import_records
    source=tmp_path/'old.db';old=sqlite3.connect(source)
    old.executescript('CREATE TABLE Challenge(id TEXT,startDate TEXT,createdAt TEXT); CREATE TABLE DailyReflection(id TEXT,challengeId TEXT,date TEXT,good TEXT,nextActions TEXT);')
    old.execute('INSERT INTO Challenge VALUES (?,?,?)',('old-challenge',shift(today(),-5),'2026-11-01T00:00:00Z'))
    old.execute('INSERT INTO DailyReflection VALUES (?,?,?,?,?)',('old-reflection','old-challenge',today(),'preserved','["walk"]'))
    old.executescript('''
    CREATE TABLE Habit(id TEXT,challengeId TEXT,categoryId INTEGER,name TEXT,frequency TEXT,weekdays TEXT,target TEXT,memo TEXT,startDate TEXT,endDate TEXT);
    CREATE TABLE HabitLog(id TEXT,habitId TEXT,date TEXT,completed INTEGER,memo TEXT);
    CREATE TABLE CategoryAssessment(id TEXT,challengeId TEXT,categoryId INTEGER,date TEXT,score INTEGER,targetScore INTEGER,actionGoal TEXT,reflection TEXT);
    CREATE TABLE EmotionLog(id TEXT,challengeId TEXT,date TEXT,fact TEXT,emotion TEXT,interpretation TEXT,alternative TEXT,action TEXT);
    CREATE TABLE BodyMeasurement(id TEXT,challengeId TEXT,date TEXT,weight REAL,waist REAL);
    CREATE TABLE WorkoutSession(id TEXT,challengeId TEXT,date TEXT,menu TEXT,memo TEXT);
    CREATE TABLE WorkoutSet(id TEXT,sessionId TEXT,exercise TEXT,setNumber INTEGER,weight REAL,reps INTEGER,seconds INTEGER);
    CREATE TABLE WeeklyReview(id TEXT,challengeId TEXT,weekStart TEXT,accomplished TEXT,improve TEXT,priority TEXT,snapshot TEXT);
    CREATE TABLE UserSettings(id INTEGER,age INTEGER,height REAL,targetWeight REAL,exerciseHabit TEXT);
    ''')
    old.execute('INSERT INTO Habit VALUES (?,?,?,?,?,?,?,?,?,?)',('h','old-challenge',1,'読書','daily','[]','10分','memo',shift(today(),-5),None))
    old.execute('INSERT INTO HabitLog VALUES (?,?,?,?,?)',('hl','h',today(),1,'log memo'))
    old.execute('INSERT INTO CategoryAssessment VALUES (?,?,?,?,?,?,?,?)',('a','old-challenge',1,today(),6,8,'goal','review'))
    old.execute('INSERT INTO EmotionLog VALUES (?,?,?,?,?,?,?,?)',('e','old-challenge',today(),'fact','emotion','interpretation','alternative','next action'))
    old.execute('INSERT INTO BodyMeasurement VALUES (?,?,?,?,?)',('b','old-challenge',today(),72,80))
    old.execute('INSERT INTO WorkoutSession VALUES (?,?,?,?,?)',('w','old-challenge',today(),'bench','workout memo'))
    old.execute('INSERT INTO WorkoutSet VALUES (?,?,?,?,?,?,?)',('ws','w','bench',1,50,10,None))
    old.execute('INSERT INTO WeeklyReview VALUES (?,?,?,?,?,?,?)',('r','old-challenge',monday(today()),'done','improve','priority','{"habitAchievement":75}'))
    old.execute('INSERT INTO UserSettings VALUES (?,?,?,?,?)',(1,23,178,76,'週2回'))
    old.commit();old.close();digest=hashlib.sha256(source.read_bytes()).hexdigest()
    with app.app_context():
        assert import_records(source,'owner')==1
        assert import_records(source,'owner')==0
    assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
    migrate(app.config)
    assert len(query('SELECT * FROM users'))==2
    assert len(query('SELECT * FROM growth_challenges WHERE user_id=1'))==1
    assert len(query('SELECT * FROM growth_challenges WHERE user_id=2'))==0
    assert client().get('/growth/reflection').status_code==200
    assert 'preserved' in client().get('/growth/reflection').get_data(as_text=True)
    assert query('SELECT memo FROM growth_habit_logs')[0]['memo']=='log memo'
    assert len(query('SELECT * FROM growth_emotions'))==1
    workout=json.loads(query('SELECT payload FROM growth_workouts')[0]['payload'])
    assert workout['sets'][0]['weight']==50
    assert json.loads(query('SELECT payload FROM growth_reviews')[0]['payload'])['legacy_snapshot']['habitAchievement']==75
    assert json.loads(query('SELECT payload FROM growth_profiles')[0]['payload'])['targetWeight']==76
    assert client().get('/growth/body').status_code==200
    assert client().get('/growth/review').status_code==200
