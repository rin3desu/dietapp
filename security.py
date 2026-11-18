import hmac
import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit
from flask import abort, jsonify, request, session


def configure_app(app):
    app.config.update(DATABASE_URL=os.getenv('DATABASE_URL'), SQLITE_PATH=os.getenv('SQLITE_PATH', str(Path(app.instance_path) / 'stoiq-local.db')), GEMINI_API_KEY=os.getenv('GEMINI_API_KEY'), GEMINI_MODEL=os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'), AI_DAILY_LIMIT=int(os.getenv('AI_DAILY_LIMIT', '10')), MAX_CONTENT_LENGTH=6 * 1024 * 1024, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=bool(os.getenv('RENDER') or os.getenv('PUBLIC_ORIGIN', '').startswith('https://')))
    if os.getenv('RENDER') and not app.config['DATABASE_URL']:
        raise RuntimeError('公開環境ではDATABASE_URLを設定してください。')
    secret = os.getenv('SECRET_KEY')
    if not secret:
        if os.getenv('RENDER'):
            configured_path = os.getenv('SESSION_KEY_FILE')
            if not configured_path and not Path('/var/data').is_dir():
                raise RuntimeError('SECRET_KEYまたは永続ディスク上のSESSION_KEY_FILEを設定してください。')
            key_file = Path(configured_path or '/var/data/stoiq/.session-key')
        else:
            key_file = Path(app.instance_path) / '.session-key'
        key_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'w', encoding='utf-8') as f:
                f.write(secrets.token_hex(32))
        except FileExistsError:
            pass
        secret = key_file.read_text(encoding='utf-8')
        if len(secret.strip()) < 32:
            raise RuntimeError('セッション署名キーが不正です。')
    app.secret_key = secret


def csrf_token():
    if '_csrf' not in session:
        session['_csrf'] = secrets.token_urlsafe(32)
    return session['_csrf']


def install_security(app):
    @app.context_processor
    def helpers():
        return dict(csrf_token=csrf_token, app_name='STOIQ')

    @app.before_request
    def protect_writes():
        if request.method not in {'POST', 'PUT', 'PATCH', 'DELETE'}:
            return None
        origin = request.headers.get('Origin')
        expected = os.getenv('PUBLIC_ORIGIN') or os.getenv('RENDER_EXTERNAL_URL') or request.host_url.rstrip('/')
        if origin and urlsplit(origin).netloc != urlsplit(expected).netloc:
            abort(403)
        supplied = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token', '')
        stored = session.get('_csrf', '')
        if not supplied or not stored or not hmac.compare_digest(supplied, stored):
            if request.is_json:
                return jsonify(error='ページを再読み込みしてから、もう一度操作してください。'), 403
            abort(403)

    @app.after_request
    def response_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        if request.path.startswith('/growth') or request.path.startswith('/food/mine') or session.get('user_id'):
            response.headers['Cache-Control'] = 'private, no-store'
        return response
