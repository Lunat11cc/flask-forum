from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.secret_key = '12635675@^%@^&%7826'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    profile_picture = db.Column(db.String(100))

    def __init__(self, username, email, password, profile_picture=None):
        self.username = username
        self.email = email
        self.password = password
        self.profile_picture = profile_picture

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)


class Forum(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)


class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    forum_id = db.Column(db.Integer, db.ForeignKey('forum.id'), nullable=False)
    forum = db.relationship('Forum', backref=db.backref('topics', lazy=True))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('topics', lazy=True))


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('comments', lazy=True))
    topic = db.relationship('Topic', backref=db.backref('comments', lazy=True))


def login_required(func):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        user = User.query.get(session['user_id'])
        return func(user=user, *args, **kwargs)

    return wrapper


@app.route('/')
def start():
    return render_template('start.html')


formats = {'png', 'jpg', 'jpeg'}


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect('/home')

    if request.method == 'POST':
        username, email, password = (
            request.form['username'],
            request.form['email'],
            request.form['password']
        )

        if len(username) >= 4 and len(email) > 4 and len(password) >= 8:
            hashed_password = bcrypt.generate_password_hash(password)

            profile_picture = request.files['profile_picture']
            if profile_picture and profile_picture.filename.rsplit('.', 1)[1].lower() in formats:
                filename = secure_filename(profile_picture.filename)
                profile_picture.save(os.path.join(
                    app.config['UPLOAD_FOLDER'], filename))
            else:
                filename = None

            new_user = User(username=username, email=email,
                            password=hashed_password, profile_picture=filename)
            db.session.add(new_user)
            db.session.commit()
            return redirect('/login')
        else:
            return 'Ошибка валидации!'

    return render_template('auth.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect('/home')

    if request.method == 'POST':
        email, password = (
            request.form['email'],
            request.form['password']
        )

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            return redirect('/home')

    return render_template('auth.html')


@login_required
@app.route('/home')
def home():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        photo_path = url_for('static', filename='uploads/' + user.profile_picture) if user.profile_picture else None
        return render_template('home.html', user=user, photo_path=photo_path)
    else:
        return redirect('/login')


@login_required
@app.route('/profile')
def profile():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        return render_template('profile.html', user=user)
    else:
        return redirect('/login')


@login_required
@app.route('/forums')
def forum_list():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    forums = Forum.query.all()
    return render_template('forums.html', user=user, forums=forums)


@login_required
@app.route('/create_forum', methods=['GET', 'POST'])
def create_forum():
    user_id = session.get('user_id')
    user = User.query.get(user_id)

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']

        new_forum = Forum(title=title, description=description)
        db.session.add(new_forum)
        db.session.commit()

        return redirect(url_for('forum_list'))

    return render_template('create_forum.html', user=user)


@login_required
@app.route('/topics/<int:forum_id>')
def topic_list(forum_id):
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    forum = Forum.query.get(forum_id)
    topics = Topic.query.filter_by(forum_id=forum_id).all()
    return render_template('topics.html', user=user, forum=forum, topics=topics)


@login_required
@app.route('/new_topic/<int:user_id>/<int:forum_id>', methods=['GET', 'POST'])
def new_topic(user_id, forum_id):
    user = User.query.get(user_id)
    forum = Forum.query.get(forum_id)

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        new_topic = Topic(title=title, content=content, forum=forum, user=user)
        db.session.add(new_topic)
        db.session.commit()

        return redirect(url_for('topic', topic_id=new_topic.id))

    return render_template('new_topic.html', forum=forum, user=user)


@login_required
@app.route('/topic/<int:topic_id>')
def topic(topic_id):
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        topic = Topic.query.get(topic_id)
        return render_template('topic.html', user=user, topic=topic, current_user=user)
    else:
        return redirect('/login')


@login_required
@app.route('/topic/<int:topic_id>/add_comment', methods=['POST'])
def add_comment(topic_id):
    content = request.form['content']
    user_id = session['user_id']

    new_comment = Comment(content=content, topic_id=topic_id, user_id=user_id)
    db.session.add(new_comment)
    db.session.commit()

    return redirect(url_for('topic', topic_id=topic_id))


@login_required
@app.route('/comment/<int:comment_id>/delete', methods=['POST'])
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)

    if comment.user_id == session['user_id']:
        db.session.delete(comment)
        db.session.commit()

    return redirect(url_for('topic', topic_id=comment.topic_id))


@login_required
@app.route('/topic/<int:topic_id>/delete', methods=['POST'])
def delete_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)

    if topic.user_id == session['user_id']:
        db.session.delete(topic)
        db.session.commit()

    return redirect(url_for('forum_list'))


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
