import os
import uuid
import hashlib
import mimetypes
import zipfile
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, send_file, flash, current_app, session
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from app.models import insert_file, get_all_files, get_file, delete_file_record

main = Blueprint('main', __name__)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Access denied')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        for user in current_app.config['AUTH_USERS']:
            if user['username'] == username and check_password_hash(user['password'], password):
                session['authenticated'] = True
                session['username'] = user['username']
                session['role'] = user.get('role', 'prof')
                return redirect(url_for('main.index'))
        flash('Invalid credentials')
    return render_template('login.html')

@main.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.login'))

@main.route('/')
@login_required
def index():
    files = get_all_files()
    return render_template('index.html', files=files)

@main.route('/upload', methods=['POST'])
@login_required
def upload():
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(url_for('main.index'))

    file = request.files['file']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('main.index'))

    confirm_pw = request.form.get('confirm_password')
    if not check_password_hash(current_app.config['CONFIRM_PASSWORD'], confirm_pw):
        flash('Invalid confirmation password')
        return redirect(url_for('main.index'))

    if file:
        original_name = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())
        zip_filename = f"{unique_id}.zip"
        zip_path = os.path.join(current_app.config['UPLOAD_FOLDER'], zip_filename)

        temp_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, original_name)
        file.save(temp_path)

        file_size = os.path.getsize(temp_path)
        zip_size = 0

        mime_type = mimetypes.guess_type(original_name)[0] or 'application/octet-stream'

        sha256 = hashlib.sha256()
        with open(temp_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        file_hash = sha256.hexdigest()

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(temp_path, original_name)

        zip_size = os.path.getsize(zip_path)
        os.remove(temp_path)

        insert_file(original_name, zip_filename, file_size, zip_size, mime_type, file_hash)
        flash('File uploaded and zipped successfully!')

    return redirect(url_for('main.index'))

@main.route('/upload-folder', methods=['POST'])
@login_required
def upload_folder():
    folder_files = request.files.getlist('folder')
    has_files = folder_files and folder_files[0].filename != ''
    empty_folders_raw = request.form.get('empty_folders', '').strip()
    empty_folder_list = [f.strip() for f in empty_folders_raw.split(',') if f.strip()] if empty_folders_raw else []

    if not has_files and not empty_folder_list:
        flash('Select a folder or specify empty folders')
        return redirect(url_for('main.index'))

    confirm_pw = request.form.get('confirm_password')
    if not check_password_hash(current_app.config['CONFIRM_PASSWORD'], confirm_pw):
        flash('Invalid confirmation password')
        return redirect(url_for('main.index'))

    if has_files:
        folder_name = os.path.basename(os.path.dirname(folder_files[0].filename)) or 'folder'
    else:
        folder_name = empty_folder_list[0].split('/')[0].split('\\')[0] or 'folder'

    unique_id = str(uuid.uuid4())
    zip_filename = f"{unique_id}.zip"
    zip_path = os.path.join(current_app.config['UPLOAD_FOLDER'], zip_filename)

    temp_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp', unique_id)
    os.makedirs(temp_dir, exist_ok=True)

    total_size = 0
    saved_paths = []
    has_any_file = False
    for f in folder_files:
        if f.filename == '':
            continue
        has_any_file = True
        rel_path = f.filename
        save_path = os.path.join(temp_dir, rel_path)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        f.save(save_path)
        total_size += os.path.getsize(save_path)
        saved_paths.append((rel_path, save_path))

    sha256 = hashlib.sha256()
    for rel_path, save_path in saved_paths:
        with open(save_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
    file_hash = sha256.hexdigest() if saved_paths else hashlib.sha256(b'').hexdigest()

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for rel_path, save_path in saved_paths:
            zf.write(save_path, rel_path)
        for ef in empty_folder_list:
            ef_normalized = ef.replace('\\', '/')
            info = zipfile.ZipInfo(ef_normalized + '/')
            zf.writestr(info, '')

    zip_size = os.path.getsize(zip_path)

    for _, save_path in saved_paths:
        os.remove(save_path)
    try:
        os.rmdir(temp_dir)
    except:
        pass

    mime_type = 'application/x-zip-compressed'
    insert_file(folder_name + '.zip', zip_filename, total_size, zip_size, mime_type, file_hash)
    flash('Folder uploaded and zipped successfully!')

    return redirect(url_for('main.index'))

@main.route('/download/<int:file_id>')
@login_required
def download(file_id):
    file_record = get_file(file_id)
    if file_record is None:
        flash('File not found')
        return redirect(url_for('main.index'))

    zip_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_record['zip_name'])
    if not os.path.exists(zip_path):
        flash('File not found on disk')
        return redirect(url_for('main.index'))

    return send_file(
        zip_path,
        as_attachment=True,
        download_name=f"{file_record['original_name']}.zip"
    )

@main.route('/delete/<int:file_id>', methods=['POST'])
@login_required
@admin_required
def delete(file_id):
    file_record = get_file(file_id)
    if file_record:
        zip_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_record['zip_name'])
        if os.path.exists(zip_path):
            os.remove(zip_path)
        delete_file_record(file_id)
        flash('File deleted')

    return redirect(url_for('main.index'))

@main.route('/delete-all', methods=['POST'])
@login_required
@admin_required
def delete_all():
    files = get_all_files()
    for file_record in files:
        zip_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_record['zip_name'])
        if os.path.exists(zip_path):
            os.remove(zip_path)
        delete_file_record(file_record['id'])
    flash('All files deleted')
    return redirect(url_for('main.index'))
