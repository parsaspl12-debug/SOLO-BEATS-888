from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session, jsonify
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'static/Music'
COVER_FOLDER = 'static/covers'
LYRICS_FOLDER = 'lyrics'
CATEGORIES_FILE = 'categories.txt'
PLAYS_FILE = 'plays.txt'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['COVER_FOLDER'] = COVER_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # حداکثر ۲۰ مگابایت برای هر آپلود

for folder in [UPLOAD_FOLDER, COVER_FOLDER, LYRICS_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

@app.errorhandler(413)
def file_too_large(e):
    return 'حجم فایل بیش از حد مجاز است (حداکثر ۲۰ مگابایت). لطفاً فایل کوچک‌تری آپلود کنید.', 413

# خواندن تعداد پخش‌ها
def load_plays():
    if not os.path.exists(PLAYS_FILE):
        return {}
    plays = {}
    with open(PLAYS_FILE, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and '|' in line:
                name, count = line.rsplit('|', 1)
                try:
                    plays[name] = int(count)
                except ValueError:
                    pass
    return plays

def save_plays(plays):
    with open(PLAYS_FILE, 'w', encoding='utf-8') as f:
        for filename, count in plays.items():
            f.write(f"{filename}|{count}\n")

# خواندن دسته‌بندی‌ها
def load_categories():
    if not os.path.exists(CATEGORIES_FILE):
        return {}
    categories = {}
    with open(CATEGORIES_FILE, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split('|')
                if len(parts) == 2:
                    categories[parts[0]] = parts[1]
    return categories

# ذخیره دسته‌بندی‌ها
def save_categories(categories):
    with open(CATEGORIES_FILE, 'w', encoding='utf-8') as f:
        for filename, category in categories.items():
            f.write(f"{filename}|{category}\n")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        if password == 'Parsa46431387':
            session['admin'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='رمز عبور اشتباه است.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

@app.route('/')
def index():
    query = request.args.get('search', '').lower()
    music_files = os.listdir(UPLOAD_FOLDER)
    categories = load_categories()
    plays = load_plays()
    music_list = []

    for filename in music_files:
        if filename.endswith('.mp3') or filename.endswith('.wav'):
            name = filename.lower()
            category = categories.get(filename, 'معمولی')
            lyrics_path = f"{LYRICS_FOLDER}/{os.path.splitext(filename)[0]}.txt"
            lyrics = ''
            if os.path.exists(lyrics_path):
                with open(lyrics_path, encoding='utf-8') as f:
                    lyrics = f.read()
            # جستجو در نام آهنگ، دسته‌بندی و متن آهنگ
            searchable = f"{name} {category.lower()} {lyrics.lower()}"
            if query in searchable:
                cover_path = f"{COVER_FOLDER}/{os.path.splitext(filename)[0]}.jpg"
                cover_exists = os.path.exists(cover_path)
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else 0
                music_list.append({
                    'name': filename,
                    'display_name': os.path.splitext(filename)[0],
                    'category': category,
                    'cover': f"/{cover_path}" if cover_exists else None,
                    'lyrics': lyrics,
                    'plays': plays.get(filename, 0),
                    'mtime': mtime
                })

    # جدیدترین آهنگ‌ها اول نمایش داده شوند
    music_list.sort(key=lambda x: x['mtime'], reverse=True)

    all_categories = sorted(set(item['category'] for item in music_list))
    return render_template('index.html', music_list=music_list, admin=session.get('admin', False), search=query, all_categories=all_categories)

@app.route('/admin/lyrics')
def admin_lyrics():
    if not session.get('admin'):
        return 'دسترسی ندارید!'
    music_files = sorted(f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.mp3') or f.endswith('.wav'))
    items = []
    for filename in music_files:
        lyrics_path = os.path.join(LYRICS_FOLDER, os.path.splitext(filename)[0] + '.txt')
        lyrics = ''
        if os.path.exists(lyrics_path):
            with open(lyrics_path, encoding='utf-8') as f:
                lyrics = f.read()
        items.append({'name': filename, 'display_name': os.path.splitext(filename)[0], 'lyrics': lyrics})
    return render_template('admin_panel.html', mode='lyrics', items=items, admin=True)

@app.route('/admin/categories')
def admin_categories():
    if not session.get('admin'):
        return 'دسترسی ندارید!'
    categories = load_categories()
    music_files = sorted(f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.mp3') or f.endswith('.wav'))
    items = [{'name': f, 'display_name': os.path.splitext(f)[0], 'category': categories.get(f, 'معمولی')} for f in music_files]
    return render_template('admin_panel.html', mode='categories', items=items, admin=True)

@app.route('/admin/rename')
def admin_rename():
    if not session.get('admin'):
        return 'دسترسی ندارید!'
    categories = load_categories()
    music_files = sorted(f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.mp3') or f.endswith('.wav'))
    items = [{'name': f, 'display_name': os.path.splitext(f)[0], 'category': categories.get(f, 'معمولی')} for f in music_files]
    return render_template('admin_panel.html', mode='rename', items=items, admin=True)

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if not session.get('admin'):
        return 'دسترسی ندارید!'

    if request.method == 'POST':
        music = request.files.get('music')
        cover = request.files.get('cover')
        lyrics = request.form.get('lyrics', '')
        category = request.form.get('category', 'معمولی').strip()

        if music:
            music_filename = music.filename
            music.save(os.path.join(app.config['UPLOAD_FOLDER'], music_filename))
            if cover:
                base = os.path.splitext(music_filename)[0]
                cover.save(os.path.join(app.config['COVER_FOLDER'], base + '.jpg'))
            if lyrics.strip():
                if not os.path.exists(LYRICS_FOLDER):
                    os.makedirs(LYRICS_FOLDER)
                with open(os.path.join(LYRICS_FOLDER, os.path.splitext(music_filename)[0] + '.txt'), 'w', encoding='utf-8') as f:
                    f.write(lyrics)
            # ذخیره دسته‌بندی
            categories = load_categories()
            categories[music_filename] = category
            save_categories(categories)

            return redirect(url_for('index'))

        return 'فایل موسیقی الزامی است.'
    return render_template('upload.html', admin=session.get('admin', False))

@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    if not session.get('admin'):
        return 'دسترسی ندارید!'

    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(path):
        os.remove(path)

    cover_path = os.path.join(app.config['COVER_FOLDER'], os.path.splitext(filename)[0] + '.jpg')
    if os.path.exists(cover_path):
        os.remove(cover_path)

    lyrics_path = os.path.join(LYRICS_FOLDER, os.path.splitext(filename)[0] + '.txt')
    if os.path.exists(lyrics_path):
        os.remove(lyrics_path)

    # حذف دسته‌بندی
    categories = load_categories()
    if filename in categories:
        categories.pop(filename)
        save_categories(categories)

    return redirect(url_for('index'))

@app.route('/track_play/<filename>', methods=['POST'])
def track_play(filename):
    plays = load_plays()
    plays[filename] = plays.get(filename, 0) + 1
    save_plays(plays)
    return jsonify({'plays': plays[filename]})

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/edit_lyrics/<filename>', methods=['POST'])
def edit_lyrics(filename):
    if not session.get('admin'):
        return 'دسترسی ندارید!'

    lyrics = request.form.get('lyrics', '')
    if not os.path.exists(LYRICS_FOLDER):
        os.makedirs(LYRICS_FOLDER)
    with open(os.path.join(LYRICS_FOLDER, os.path.splitext(filename)[0] + '.txt'), 'w', encoding='utf-8') as f:
        f.write(lyrics)

    return redirect(url_for('index'))

@app.route('/edit_info/<filename>', methods=['POST'])
def edit_info(filename):
    if not session.get('admin'):
        return 'دسترسی ندارید!'

    new_name = request.form.get('new_name', '').strip()
    new_category = request.form.get('new_category', 'معمولی').strip()

    old_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    old_cover = os.path.join(app.config['COVER_FOLDER'], os.path.splitext(filename)[0] + '.jpg')
    old_lyrics = os.path.join(LYRICS_FOLDER, os.path.splitext(filename)[0] + '.txt')

    if new_name:
        new_path = os.path.join(app.config['UPLOAD_FOLDER'], new_name)
        # تغییر نام فایل موزیک
        os.rename(old_path, new_path)

        # تغییر نام کاور اگر وجود داشت
        if os.path.exists(old_cover):
            new_cover = os.path.join(app.config['COVER_FOLDER'], os.path.splitext(new_name)[0] + '.jpg')
            os.rename(old_cover, new_cover)

        # تغییر نام فایل متن اگر وجود داشت
        if os.path.exists(old_lyrics):
            new_lyrics = os.path.join(LYRICS_FOLDER, os.path.splitext(new_name)[0] + '.txt')
            os.rename(old_lyrics, new_lyrics)

        # بروزرسانی دسته‌بندی
        categories = load_categories()
        if filename in categories:
            categories.pop(filename)
        categories[new_name] = new_category
        save_categories(categories)
    else:
        # فقط آپدیت دسته‌بندی اگر نام تغییر نکرده
        categories = load_categories()
        categories[filename] = new_category
        save_categories(categories)

    return redirect(url_for('index'))

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False') == 'True'
    app.run(debug=debug_mode, host='0.0.0.0', port=port)