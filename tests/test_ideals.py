import base64
import io
import json
from types import SimpleNamespace

import pytest
from PIL import Image
from app import app
from test_stoiq import configured, client, post, query, start


def save_goal(c,**changes):
    values=dict(title='芯の強い自分',vision='人に丁寧に接し、自分との約束を守り続ける。',why='毎日の判断の軸を作りたい。',target_date='2027-02-01',person_name='架空の主人公',person_kind='fictional',person_context='物語で失敗しても他人のせいにせず、毎朝の基礎練習を続ける場面が印象に残った。',admiration='継続する姿勢と、人に対する丁寧さ。')
    values.update(changes)
    response=post(c,'/ideals/save',values)
    assert response.status_code==302
    return query('SELECT * FROM ideal_goals WHERE user_id=1')[0]


def analysis_payload():
    return dict(summary='積み重ねを自分の行動の軸にする。',qualities=[dict(trait='継続する姿勢',evidence='毎朝の基礎練習という入力',interpretation='結果より過程を大切にする点に魅力を感じている可能性。')],mindsets=[dict(before='完璧にできなければ意味がない',after='小さくても続ける',practice='1分の行動を決める。')],habits=[dict(name='毎朝の準備を3分行う',cue='朝食のあと',minutes=3,category_id=5,frequency='daily',weekdays=[],reason='自分との約束を守る練習になる。'),dict(name='会話を振り返る',cue='月水金の帰宅後',minutes=5,category_id=3,frequency='days',weekdays=[1,3,5],reason='丁寧な応対を振り返る。')],first_step='明日の準備を1つ決める。',uncertainty='入力されたエピソードをもとにした仮説で、本人の内面の断定ではない。')


class FakeText:
    def __init__(self,payload=None):
        self.models=self;self.calls=[];self.payload=payload
    def generate_content(self,**kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(text=json.dumps(self.payload or analysis_payload(),ensure_ascii=False))


def jpeg(color='blue',metadata=False):
    buffer=io.BytesIO()
    picture=Image.new('RGB',(50,70),color)
    exif=Image.Exif()
    if metadata:exif[315]='PRIVATE_CAMERA_OWNER';exif[274]=6
    picture.save(buffer,'JPEG',exif=exif)
    return buffer.getvalue()


class FakeImage:
    def __init__(self,no_image=False):
        self.models=self;self.calls=[];self.no_image=no_image
    def generate_content(self,**kwargs):
        self.calls.append(kwargs)
        parts=[] if self.no_image else [SimpleNamespace(inline_data=SimpleNamespace(mime_type='image/jpeg',data=jpeg('green')))]
        return SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=parts))])


def analyze(c,row):
    return post(c,f'/ideals/{row["id"]}/analyze',json={'consent':True})


def portrait(c,row,**overrides):
    data=dict(appearance='顔立ちは残して、落ち着いた服装と自然な短髪に。',own_photo='yes',photo_consent='yes',selfie=(io.BytesIO(jpeg(metadata=True)),'private-camera-name.jpg'))
    data.update(overrides)
    return post(c,f'/ideals/{row["id"]}/portrait',data,content_type='multipart/form-data')


def test_goal_private_save_edit_and_navigation(configured):
    assert client(None).get('/ideals').status_code==302
    c=client()
    assert c.get('/ideals').status_code==200
    assert '/ideals' in c.get('/').get_data(as_text=True)
    row=save_goal(c,title='<script>private-goal</script>')
    body=c.get('/ideals').get_data(as_text=True)
    assert '&lt;script&gt;private-goal&lt;/script&gt;' in body
    assert 'private-goal' not in client(2).get('/ideals').get_data(as_text=True)
    assert c.get('/ideals').headers['Cache-Control']=='private, no-store'
    assert query('SELECT * FROM ideal_ai_usage')==[]
    save_goal(c,title='更新した理想',person_kind='real')
    assert len(query('SELECT * FROM ideal_goals WHERE user_id=1'))==1
    assert query('SELECT * FROM ideal_goals')[0]['id']==row['id']


def test_analysis_consent_validation_and_missing_key(configured):
    c=client();row=save_goal(c)
    assert post(c,f'/ideals/{row["id"]}/analyze',json={'consent':False}).status_code==400
    assert analyze(c,row).status_code==503
    assert c.post(f'/ideals/{row["id"]}/analyze',json={'consent':True}).status_code==403
    row=save_goal(c,person_context='短い説明')
    app.config['IDEAL_TEXT_CLIENT']=FakeText()
    assert analyze(c,row).status_code==400
    assert query('SELECT * FROM ideal_ai_usage')==[]


def test_analysis_allowlist_result_and_invalidation(configured):
    c=client();start(c)
    post(c,'/growth/save',{'action':'reflection','date':__import__('growth').today(),'good':'PRIVATE_DIARY'})
    fake=FakeText();app.config['IDEAL_TEXT_CLIENT']=fake
    row=save_goal(c)
    assert analyze(c,row).status_code==200
    content=fake.calls[0]['contents'];payload=json.loads(content)
    assert set(payload)=={'vision','person_name','person_kind','person_context','admiration'}
    assert 'PRIVATE_DIARY' not in content and 'owner' not in content
    assert c.get('/ideals').status_code==200
    assert '今日の一歩' in c.get('/ideals').get_data(as_text=True)
    saved=query('SELECT * FROM ideal_goals')[0]
    save_goal(c,title='目標の名前だけ変更')
    assert query('SELECT * FROM ideal_goals')[0]['revision']==saved['revision']
    save_goal(c,admiration='別の行動を大切にしたい。')
    assert query('SELECT * FROM ideal_goals')[0]['analysis'] is None


def test_habits_added_to_owned_challenge_without_duplicates(configured):
    c=client();row=save_goal(c);app.config['IDEAL_TEXT_CLIENT']=FakeText()
    analyze(c,row);row=query('SELECT * FROM ideal_goals')[0]
    url=f'/ideals/{row["id"]}/habit'
    form={'revision':row['revision'],'index':'0'}
    assert post(c,url,form).location.endswith('/growth')
    start(c)
    assert len(query('SELECT * FROM growth_habits'))==6
    assert post(c,url,form).status_code==302
    assert post(c,url,form).status_code==302
    assert len(query('SELECT * FROM growth_habits'))==7
    assert query('SELECT * FROM ideal_habit_links')[0]['habit_index']==0
    assert post(client(2),url,form).status_code==404
    assert post(c,url,{'revision':'outdated','index':'0'}).status_code==409
    assert post(c,url,{'revision':row['revision'],'index':'-1'}).status_code==400
    assert '追加済み' in c.get('/ideals').get_data(as_text=True)


def test_analysis_failure_preserves_previous_and_quota(configured):
    c=client();row=save_goal(c);app.config['IDEAL_TEXT_CLIENT']=FakeText()
    assert analyze(c,row).status_code==200
    previous=query('SELECT analysis FROM ideal_goals')[0]['analysis']
    bad=analysis_payload();bad['habits'][0]['category_id']=99
    app.config['IDEAL_TEXT_CLIENT']=FakeText(bad)
    assert analyze(c,row).status_code==502
    assert query('SELECT analysis FROM ideal_goals')[0]['analysis']==previous
    app.config['IDEAL_TEXT_DAILY_LIMIT']=2
    assert analyze(c,row).status_code==429
    assert query("SELECT count FROM ideal_ai_usage WHERE kind='text'")[0]['count']==2


def test_selfie_consent_image_validation_and_no_disk_spooling(configured):
    c=client();row=save_goal(c);fake=FakeImage();app.config['IDEAL_IMAGE_CLIENT']=fake
    assert portrait(c,row,photo_consent='no').status_code==400
    assert portrait(c,row,own_photo='no').status_code==400
    assert portrait(c,row,selfie=(io.BytesIO(b'<svg/>'),'fake.jpg')).status_code==400
    assert portrait(c,row,selfie=(io.BytesIO(b'x'*(5*1024*1024+1)),'large.jpg')).status_code==400
    assert not fake.calls and not query('SELECT * FROM ideal_ai_usage')
    from werkzeug.test import EnvironBuilder
    environ=EnvironBuilder(path=f'/ideals/{row["id"]}/portrait',method='POST').get_environ()
    req=app.request_class(environ)
    stream=req._get_file_stream(1024*1024,'image/jpeg','test.jpg',1024*1024)
    assert isinstance(stream,io.BytesIO)


def test_portrait_sends_only_clean_selfie_and_appearance_and_stays_private(configured):
    c=client();row=save_goal(c);fake=FakeImage();app.config['IDEAL_IMAGE_CLIENT']=fake
    assert portrait(c,row).status_code==200
    call=fake.calls[0]
    assert call['model']=='gemini-3.1-flash-lite-image'
    text=call['contents'][0].text
    assert row['person_name'] not in text and row['why'] not in text and row['vision'] not in text
    assert b'PRIVATE_CAMERA_OWNER' not in call['contents'][1].inline_data.data
    assert Image.open(io.BytesIO(call['contents'][1].inline_data.data)).getexif()=={}
    saved=query('SELECT * FROM ideal_goals')[0]
    assert 'PRIVATE_CAMERA_OWNER' not in json.dumps(saved)
    generated=base64.b64decode(saved['image_base64'])
    assert generated.startswith(b'\x89PNG') and generated!=jpeg()
    image_url=f'/ideals/{row["id"]}/image'
    result=c.get(image_url)
    assert result.status_code==200 and result.mimetype=='image/png'
    assert result.headers['Cache-Control']=='private, no-store'
    assert client(2).get(image_url).status_code==404
    assert client(None).get(image_url).status_code==302
    assert 'attachment' in c.get(image_url+'?download=1').headers['Content-Disposition']
    assert 'AI VISUALIZATION' in c.get('/ideals').get_data(as_text=True)
    assert post(client(2),f'/ideals/{row["id"]}/remove-image').status_code==404
    post(c,f'/ideals/{row["id"]}/remove-image')
    assert c.get(image_url).status_code==404 and query('SELECT * FROM ideal_goals')[0]['vision']==row['vision']


def test_portrait_no_image_retains_previous_and_daily_limit(configured):
    c=client();row=save_goal(c);app.config['IDEAL_IMAGE_CLIENT']=FakeImage()
    portrait(c,row)
    previous=query('SELECT image_base64 FROM ideal_goals')[0]['image_base64']
    app.config['IDEAL_IMAGE_CLIENT']=FakeImage(no_image=True)
    assert portrait(c,row).status_code==502
    assert query('SELECT image_base64 FROM ideal_goals')[0]['image_base64']==previous
    app.config['IDEAL_IMAGE_DAILY_LIMIT']=2
    assert portrait(c,row).status_code==429


def test_other_user_cannot_trigger_analysis_or_image_generation(configured):
    row=save_goal(client());other=client(2)
    assert analyze(other,row).status_code==404
    assert portrait(other,row).status_code==404
    assert query('SELECT * FROM ideal_ai_usage')==[]


def test_concurrent_goal_change_never_attaches_stale_analysis(configured):
    c=client();row=save_goal(c)
    class ConcurrentEdit(FakeText):
        def generate_content(self,**kwargs):
            from ideals import execute,db
            execute('UPDATE ideal_goals SET admiration=%s WHERE id=%s',('分析中に変更した憧れの理由。',row['id']))
            db().commit()
            return super().generate_content(**kwargs)
    app.config['IDEAL_TEXT_CLIENT']=ConcurrentEdit()
    assert analyze(c,row).status_code==409
    assert query('SELECT * FROM ideal_goals')[0]['analysis'] is None
