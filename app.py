import os
import sys
import sqlite3
import requests
import shutil
import tempfile
import zipfile
import csv
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import json
from cryptography.fernet import Fernet
import uuid
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
    data_dir = getattr(sys, '_MEIPASS', base_dir)
    # Portable runtime data stored next to the executable when frozen
    instance_path = os.path.join(base_dir, 'instance')
else:
    base_dir = os.path.abspath(os.path.dirname(__file__))
    data_dir = base_dir
    instance_path = os.path.join(base_dir, 'instance')

template_folder = os.path.join(data_dir, 'templates')
static_folder = os.path.join(data_dir, 'static')
poster_folder = os.path.join(instance_path, 'posters')

app = Flask(__name__, instance_relative_config=True, template_folder=template_folder, static_folder=static_folder)
app.config.from_mapping(
    SECRET_KEY='plex-cataloger-secret-key-change-in-production',
    SQLALCHEMY_DATABASE_URI='sqlite:///' + os.path.join(instance_path, 'plex_catalog.db'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    UPLOAD_FOLDER=poster_folder,
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
    EXPORT_FOLDER=os.path.join(instance_path, 'exports')
)

os.makedirs(instance_path, exist_ok=True)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

if not os.path.exists(app.config['EXPORT_FOLDER']):
    os.makedirs(app.config['EXPORT_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


# --- Encryption key for storing tokens ---
secret_key_path = os.path.join(instance_path, 'secret.key')
if not os.path.exists(secret_key_path):
    # generate and save a key
    k = Fernet.generate_key()
    with open(secret_key_path, 'wb') as kf:
        kf.write(k)
else:
    with open(secret_key_path, 'rb') as kf:
        k = kf.read()

fernet = Fernet(k)


class Settings(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    plex_url = db.Column(db.String(255))
    plex_token_enc = db.Column(db.Text)
    library_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_token(self):
        if not self.plex_token_enc:
            return None
        try:
            return fernet.decrypt(self.plex_token_enc.encode('utf-8')).decode('utf-8')
        except Exception:
            return None

    def set_token(self, token_plain):
        if token_plain is None:
            self.plex_token_enc = None
        else:
            self.plex_token_enc = fernet.encrypt(token_plain.encode('utf-8')).decode('utf-8')

class Library(db.Model):
    __tablename__ = 'libraries'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    plex_key = db.Column(db.String(50), unique=True)
    item_type = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('CatalogItem', backref='library', lazy=True, cascade='all, delete-orphan')

class CatalogItem(db.Model):
    __tablename__ = 'catalog_items'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    year = db.Column(db.Integer)
    summary = db.Column(db.Text)
    rating = db.Column(db.Float)
    poster_filename = db.Column(db.String(255))
    genres = db.Column(db.String(255))
    duration = db.Column(db.Integer)
    plex_key = db.Column(db.String(50), unique=True)
    plex_title = db.Column(db.String(200))
    plex_rating = db.Column(db.String(20))
    plex_content_rating = db.Column(db.String(20))
    plex_studio = db.Column(db.String(100))
    plex_added_at = db.Column(db.DateTime)
    plex_updated_at = db.Column(db.DateTime)
    director = db.Column(db.String(100))
    actors = db.Column(db.Text)
    trailer_url = db.Column(db.String(255))
    website_url = db.Column(db.String(255))
    custom_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    library_id = db.Column(db.Integer, db.ForeignKey('libraries.id'), nullable=False)

class ExportJob(db.Model):
    __tablename__ = 'export_jobs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    format = db.Column(db.String(20), nullable=False)
    filename = db.Column(db.String(255))
    library_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    record_count = db.Column(db.Integer)

with app.app_context():
    db.create_all()
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['EXPORT_FOLDER'], exist_ok=True)

    # ensure settings table exists for the new model
    try:
        db.create_all()
    except Exception:
        pass

    # migrate legacy settings.json into DB if present
    legacy_settings_path = os.path.join(app.instance_path, 'settings.json')
    try:
        if os.path.exists(legacy_settings_path):
            with open(legacy_settings_path, 'r', encoding='utf-8') as lf:
                data = json.load(lf) or {}
            if data.get('plex_url') and data.get('plex_token'):
                exists = Settings.query.filter_by(plex_url=data.get('plex_url'), library_name=data.get('library_name')).first()
                if not exists:
                    s = Settings(plex_url=data.get('plex_url'), library_name=data.get('library_name'))
                    s.set_token(data.get('plex_token'))
                    db.session.add(s)
                    db.session.commit()
            # rename legacy file to preserve backup
            try:
                os.rename(legacy_settings_path, legacy_settings_path + '.bak')
            except Exception:
                pass
    except Exception:
        pass

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def download_plex_poster(server, item, plex_token=None):
    poster_path = getattr(item, 'thumb', None) or getattr(item, 'poster', None)
    if not poster_path:
        return None, None

    try:
        url = server.url(poster_path)
        headers = {
            'Accept': 'image/jpeg,image/png,image/webp,image/*,*/*'
        }
        if plex_token:
            headers['X-Plex-Token'] = plex_token

        img_resp = requests.get(url, headers=headers, timeout=30, verify=False)
        img_resp.raise_for_status()
        content_type = (img_resp.headers.get('Content-Type', '') or '').lower()
        if not content_type.startswith('image/'):
            return None, f"Poster download failed for '{getattr(item, 'title', 'unknown')}': invalid content type {content_type}"

        if 'png' in content_type:
            ext = 'png'
        elif 'gif' in content_type:
            ext = 'gif'
        elif 'webp' in content_type:
            ext = 'webp'
        elif 'jpeg' in content_type or 'jpg' in content_type:
            ext = 'jpg'
        else:
            ext = 'jpg'

        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(filepath, 'wb') as f:
            f.write(img_resp.content)
        return filename, None
    except Exception as e:
        return None, f"Poster download failed for '{getattr(item, 'title', 'unknown')}': {e}"

def get_plex_connection(plex_url=None, plex_token=None):
    try:
        from plexapi.server import PlexServer
        if plex_url and plex_token:
            return PlexServer(plex_url, plex_token)
        return None
    except Exception as e:
        print(f"Plex connection error: {e}")
        return None

def import_from_plex(plex_url, plex_token, library_name=None):
    try:
        from plexapi.server import PlexServer
        server = PlexServer(plex_url, plex_token)
        results = {'imported': 0, 'updated': 0, 'errors': []}
        
        libraries = [server.library.section(library_name)] if library_name else server.library.sections()
        
        for section in libraries:
            if section.type not in ['movie', 'show']:
                continue
            
            lib = Library.query.filter_by(plex_key=str(section.key)).first()
            if not lib:
                lib = Library(name=section.title, plex_key=str(section.key), item_type=section.type)
                db.session.add(lib)
                db.session.commit()
            
            all_items = section.all()
            for item in all_items:
                try:
                    existing = CatalogItem.query.filter_by(plex_key=str(item.ratingKey)).first()
                    
                    poster_filename, poster_error = download_plex_poster(server, item, plex_token=plex_token)
                    if poster_error:
                        results['errors'].append(poster_error)

                    genres = ', '.join([g.tag for g in item.genres]) if hasattr(item, 'genres') else ''
                    actors = ', '.join([r.tag for r in item.roles]) if hasattr(item, 'roles') else ''

                    item_data = {
                        'title': item.title,
                        'year': item.year if hasattr(item, 'year') else None,
                        'summary': item.summary if hasattr(item, 'summary') else '',
                        'rating': float(item.rating) if hasattr(item, 'rating') and item.rating else None,
                        'poster_filename': poster_filename,
                        'genres': genres,
                        'duration': item.duration if hasattr(item, 'duration') else None,
                        'plex_key': str(item.ratingKey),
                        'plex_title': item.title,
                        'plex_rating': str(item.contentRating) if hasattr(item, 'contentRating') else '',
                        'plex_content_rating': str(item.contentRating) if hasattr(item, 'contentRating') else '',
                        'plex_studio': item.studio if hasattr(item, 'studio') else '',
                        'plex_added_at': datetime.fromtimestamp(int(item.addedAt)) if (hasattr(item, 'addedAt') and item.addedAt and not hasattr(item.addedAt, 'year')) else getattr(item, 'addedAt', None),
                        'plex_updated_at': datetime.fromtimestamp(int(item.updatedAt)) if (hasattr(item, 'updatedAt') and item.updatedAt and not hasattr(item.updatedAt, 'year')) else getattr(item, 'updatedAt', None),
                        'director': '',
                        'actors': actors,
                        'library_id': lib.id
                    }
                    
                    if hasattr(item, 'directors'):
                        item_data['director'] = ', '.join([d.tag for d in item.directors])
                    
                    if existing:
                        for key, value in item_data.items():
                            if value is not None:
                                setattr(existing, key, value)
                        results['updated'] += 1
                    else:
                        new_item = CatalogItem(**item_data)
                        db.session.add(new_item)
                        results['imported'] += 1
                    
                except Exception as e:
                    results['errors'].append(f"Error importing {item.title if hasattr(item, 'title') else 'unknown'}: {str(e)}")
            
            db.session.commit()
        
        return results
    except Exception as e:
        return {'imported': 0, 'updated': 0, 'errors': [str(e)]}

@app.route('/')
def index():
    libraries = Library.query.all()
    total_items = CatalogItem.query.count()
    return render_template('index.html', libraries=libraries, total_items=total_items)

@app.route('/import', methods=['GET', 'POST'])
def import_page():
    settings_path = os.path.join(app.instance_path, 'settings.json')

    if request.method == 'POST':
        plex_url = request.form.get('plex_url')
        plex_token = request.form.get('plex_token')
        library_name = request.form.get('library_name') or None

        if not plex_url or not plex_token:
            flash('Plex URL and Token are required', 'error')
            return redirect(url_for('import_page'))

        results = import_from_plex(plex_url, plex_token, library_name)

        # Persist plex connection info to DB (encrypted)
        try:
            existing = Settings.query.filter_by(plex_url=plex_url, library_name=library_name).first()
            if existing:
                existing.set_token(plex_token)
            else:
                s = Settings(plex_url=plex_url, library_name=library_name)
                s.set_token(plex_token)
                db.session.add(s)
            db.session.commit()
        except Exception as e:
            print('Failed to save settings to DB:', e)

        if results['errors']:
            flash(f"Import completed with {results['imported']} new, {results['updated']} updated, {len(results['errors'])} errors", 'warning')
        else:
            flash(f"Successfully imported {results['imported']} new items and updated {results['updated']} items", 'success')

        return redirect(url_for('catalog'))

    # GET: try to pre-fill with last saved settings from DB and provide list of saved connections
    saved = {}
    saved_list = []
    try:
        s = Settings.query.order_by(Settings.updated_at.desc()).first()
        if s:
            saved = {
                'plex_url': s.plex_url,
                'plex_token': s.get_token(),
                'library_name': s.library_name
            }
        saved_list = Settings.query.order_by(Settings.updated_at.desc()).all()
    except Exception:
        saved = {}
        saved_list = []

    return render_template('import.html', plex_url=saved.get('plex_url'), plex_token=saved.get('plex_token'), library_name=saved.get('library_name'), saved_settings=saved_list)

@app.route('/catalog')
@app.route('/catalog/<int:library_id>')
def catalog(library_id=None):
    page = request.args.get('page', 1, type=int)
    per_page = 24
    
    query = CatalogItem.query
    if library_id:
        query = query.filter_by(library_id=library_id)
        library = Library.query.get_or_404(library_id)
    else:
        library = None
    
    pagination = query.order_by(CatalogItem.title).paginate(page=page, per_page=per_page, error_out=False)
    items = pagination.items
    libraries = Library.query.all()
    
    return render_template('catalog.html', items=items, pagination=pagination, 
                         library=library, libraries=libraries)

def get_database_path():
    uri = app.config['SQLALCHEMY_DATABASE_URI']
    if uri.startswith('sqlite:///'):
        return uri.replace('sqlite:///', '', 1)
    raise RuntimeError('Unsupported database URI for browsing')

def get_database_tables():
    db_path = get_database_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    tables = [row['name'] for row in cur.fetchall()]
    conn.close()
    return tables

@app.route('/database')
@app.route('/database/<table_name>')
def database_browser(table_name=None):
    tables = get_database_tables()
    table_info = []
    for table in tables:
        conn = sqlite3.connect(get_database_path())
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM \"{table}\"")
        count = cur.fetchone()[0]
        conn.close()
        table_info.append({'name': table, 'count': count})

    selected_table = None
    columns = []
    rows = []
    if table_name:
        if table_name not in tables:
            abort(404)

        selected_table = table_name
        conn = sqlite3.connect(get_database_path())
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM \"{table_name}\" LIMIT 200")
        rows = cur.fetchall()
        columns = rows[0].keys() if rows else []
        conn.close()

    return render_template('database_browser.html', tables=table_info, selected_table=selected_table, columns=columns, rows=rows)


@app.route('/settings', methods=['GET', 'POST'])
def settings_page():
    if request.method == 'POST':
        plex_url = request.form.get('plex_url')
        plex_token = request.form.get('plex_token')
        library_name = request.form.get('library_name') or None

        if not plex_url or not plex_token:
            flash('Plex URL and Token are required', 'error')
            return redirect(url_for('settings_page'))

        try:
            s = Settings(plex_url=plex_url, library_name=library_name)
            s.set_token(plex_token)
            db.session.add(s)
            db.session.commit()
            flash('Connection saved', 'success')
        except Exception as e:
            print('Failed to save setting:', e)
            flash('Failed to save connection', 'error')

        return redirect(url_for('settings_page'))

    settings = Settings.query.order_by(Settings.updated_at.desc()).all()
    return render_template('settings.html', settings=settings)


@app.route('/settings/<int:id>/delete', methods=['POST'])
def delete_setting(id):
    s = Settings.query.get_or_404(id)
    db.session.delete(s)
    db.session.commit()
    flash('Connection deleted', 'success')
    return redirect(url_for('settings_page'))

@app.route('/item/<int:item_id>')
def item_detail(item_id):
    item = CatalogItem.query.get_or_404(item_id)
    return render_template('item_detail.html', item=item)

@app.route('/item/<int:item_id>/edit', methods=['GET', 'POST'])
def edit_item(item_id):
    item = CatalogItem.query.get_or_404(item_id)
    
    if request.method == 'POST':
        item.title = request.form.get('title', item.title)
        item.year = request.form.get('year', type=int)
        item.summary = request.form.get('summary', item.summary)
        item.rating = request.form.get('rating', type=float)
        item.genres = request.form.get('genres', item.genres)
        item.director = request.form.get('director', item.director)
        item.actors = request.form.get('actors', item.actors)
        item.plex_studio = request.form.get('studio', item.plex_studio)
        item.custom_notes = request.form.get('custom_notes', item.custom_notes)
        item.website_url = request.form.get('website_url', item.website_url)
        item.trailer_url = request.form.get('trailer_url', item.trailer_url)
        
        poster_file = request.files.get('poster')
        if poster_file and poster_file.filename and allowed_file(poster_file.filename):
            filename = secure_filename(f"{uuid.uuid4().hex}_{poster_file.filename}")
            poster_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            if item.poster_filename:
                old_path = os.path.join(app.config['UPLOAD_FOLDER'], item.poster_filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
            item.poster_filename = filename
        
        db.session.commit()
        flash('Item updated successfully', 'success')
        return redirect(url_for('item_detail', item_id=item.id))
    
    return render_template('edit_item.html', item=item)

@app.route('/item/<int:item_id>/delete', methods=['POST'])
def delete_item(item_id):
    item = CatalogItem.query.get_or_404(item_id)
    if item.poster_filename:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], item.poster_filename)
        if os.path.exists(filepath):
            os.remove(filepath)
    db.session.delete(item)
    db.session.commit()
    flash('Item deleted', 'success')
    return redirect(url_for('catalog'))

@app.route('/library/<int:library_id>/delete', methods=['POST'])
def delete_library(library_id):
    library = Library.query.get_or_404(library_id)
    for item in library.items:
        if item.poster_filename:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], item.poster_filename)
            if os.path.exists(filepath):
                os.remove(filepath)
    db.session.delete(library)
    db.session.commit()
    flash('Library deleted', 'success')
    return redirect(url_for('index'))

@app.route('/export')
@app.route('/export/<int:library_id>')
def export_page(library_id=None):
    libraries = Library.query.all()
    library = Library.query.get(library_id) if library_id else None
    exports = ExportJob.query.order_by(ExportJob.created_at.desc()).limit(20).all()
    return render_template('export.html', libraries=libraries, library=library, exports=exports)

@app.route('/export/generate', methods=['POST'])
def generate_export():
    export_format = request.form.get('format', 'json')
    library_id = request.form.get('library_id')
    export_name = request.form.get('name', f'export_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
    include_posters = request.form.get('include_posters') == 'on'
    
    query = CatalogItem.query
    if library_id:
        query = query.filter_by(library_id=int(library_id))
    items = query.all()
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if export_format == 'json':
        data = []
        for item in items:
            data.append({
                'id': item.id,
                'title': item.title,
                'year': item.year,
                'summary': item.summary,
                'rating': item.rating,
                'genres': item.genres,
                'duration': item.duration,
                'director': item.director,
                'actors': item.actors,
                'poster_filename': item.poster_filename,
                'plex_title': item.plex_title,
                'plex_rating': item.plex_rating,
                'plex_content_rating': item.plex_content_rating,
                'plex_studio': item.plex_studio,
                'website_url': item.website_url,
                'trailer_url': item.trailer_url,
                'custom_notes': item.custom_notes
            })
        
        filename = f"{export_name}_{timestamp}.json"
        filepath = os.path.join(app.config['EXPORT_FOLDER'], filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    elif export_format == 'html':
        filename = f"{export_name}_{timestamp}.html"
        filepath = os.path.join(app.config['EXPORT_FOLDER'], filename)

        html_content = render_template('export_template.html', items=items, include_posters=include_posters)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        if include_posters:
            posters_dir = os.path.join(app.config['EXPORT_FOLDER'], 'posters')
            os.makedirs(posters_dir, exist_ok=True)
            for item in items:
                if item.poster_filename:
                    src_path = os.path.join(app.config['UPLOAD_FOLDER'], item.poster_filename)
                    if os.path.exists(src_path):
                        dst_path = os.path.join(posters_dir, item.poster_filename)
                        if not os.path.exists(dst_path):
                            shutil.copy2(src_path, dst_path)
    
    elif export_format == 'csv':
        filename = f"{export_name}_{timestamp}.csv"
        filepath = os.path.join(app.config['EXPORT_FOLDER'], filename)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Title', 'Year', 'Summary', 'Rating', 'Genres', 'Duration', 'Director', 'Actors', 'Website', 'Custom Notes'])
            for item in items:
                writer.writerow([
                    item.title, item.year, item.summary, item.rating,
                    item.genres, item.duration, item.director, item.actors,
                    item.website_url, item.custom_notes
                ])
    
    job = ExportJob(name=export_name, format=export_format, filename=filename,
                    library_id=int(library_id) if library_id else None, record_count=len(items))
    db.session.add(job)
    db.session.commit()
    
    flash(f'Export generated: {filename} ({len(items)} records)', 'success')
    return redirect(url_for('export_page'))

@app.route('/export/download/<filename>')
def download_export(filename):
    filepath = os.path.join(app.config['EXPORT_FOLDER'], filename)
    if os.path.exists(filepath):
        posters_dir = os.path.join(app.config['EXPORT_FOLDER'], 'posters')
        has_posters = False
        if filename.endswith('.html') and os.path.exists(posters_dir):
            try:
                files = os.listdir(posters_dir)
                has_posters = bool(files)
            except OSError:
                has_posters = False
        if has_posters:
            temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(filepath, os.path.basename(filepath))
                for poster in os.listdir(posters_dir):
                    poster_path = os.path.join(posters_dir, poster)
                    if os.path.isfile(poster_path):
                        zf.write(poster_path, os.path.join('posters', poster))
            temp_zip.close()
            response = send_file(temp_zip.name, as_attachment=True, download_name=f'{filename}.zip', mimetype='application/zip')
            os.unlink(temp_zip.name)
            return response
        return send_file(filepath, as_attachment=True)
    flash('File not found', 'error')
    return redirect(url_for('export_page'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/posters/<path:filename>')
def poster_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
