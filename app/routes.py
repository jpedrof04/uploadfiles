import os
import uuid
import zipfile
from flask import Blueprint, render_template, request, redirect, url_for, send_file, flash, current_app
from werkzeug.utils import secure_filename
from app.models import insert_file, get_all_files, get_file, delete_file_record

main = Blueprint('main', __name__)

@main.route('/')
def index():
    files = get_all_files()
    return render_template('index.html', files=files)

@main.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(url_for('main.index'))

    file = request.files['file']
    if file.filename == '':
        flash('No file selected')
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

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(temp_path, original_name)

        os.remove(temp_path)

        insert_file(original_name, zip_filename, file_size)
        flash('File uploaded and zipped successfully!')

    return redirect(url_for('main.index'))

@main.route('/download/<int:file_id>')
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
def delete(file_id):
    file_record = get_file(file_id)
    if file_record:
        zip_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_record['zip_name'])
        if os.path.exists(zip_path):
            os.remove(zip_path)
        delete_file_record(file_id)
        flash('File deleted')

    return redirect(url_for('main.index'))
