import datetime, os, random, string
from flask import Flask, request, render_template, session, url_for, redirect
from flask_babelex import Babel
from flask_sqlalchemy import SQLAlchemy
from flask_user import current_user, login_required, roles_required, UserManager, UserMixin
from flask_admin import Admin
from faker import Faker

class ConfigClass(object):
    """ Flask application config """

    # Flask settings
    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!'

    # Flask-SQLAlchemy settings
    SQLALCHEMY_DATABASE_URI = 'sqlite:///blog.db'    # File-based SQL database
    SQLALCHEMY_TRACK_MODIFICATIONS = False    # Avoids SQLAlchemy warning

    # Flask-Mail SMTP server settings
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USE_TLS = False
    MAIL_USERNAME = 'email@example.com'
    MAIL_PASSWORD = 'password'
    MAIL_DEFAULT_SENDER = '"MyApp" <noreply@example.com>'

    # Flask-User settings
    USER_APP_NAME = "PAPERBLOG"      # Shown in and email templates and page footers
    USER_ENABLE_EMAIL = False        # Enable email authentication
    USER_ENABLE_USERNAME = True # Disable username authentication
    USER_EMAIL_SENDER_NAME = USER_APP_NAME
    USER_EMAIL_SENDER_EMAIL = "noreply@example.com"

app = Flask(__name__)

# Class-based application configuration
# image-upload settings
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = set(['jpeg', 'jpg', 'png', 'gif'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config.from_object(__name__+'.ConfigClass')
# Initialize Flask-BabelEx
babel = Babel(app)
# Initialize Flask-SQLAlchemy
db = SQLAlchemy(app)

# faker init

fake = Faker()

# Define the User data-model.
# NB: Make sure to add flask_user UserMixin !!!

class Categories(db.Model):
    __tablename_ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(120), nullable=False)
    posts = db.relationship('Pages', backref='post', lazy='dynamic')
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class Pages(db.Model):
    __tablename__ = 'pages'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.Integer, db.ForeignKey('categories.id'))
    title = db.Column(db.String(1000))
    content = db.Column(db.Text())
    topic_name = db.Column(db.String(120), nullable=False)

    def __init__(self, title, content):
        self.title = title
        self.content = content

    def __repr__(self):
        return '<Pages : id=%r, title=%s, content=%s>' % (self.id, self.title, self.content)

class Notice(db.Model):
    __tablename_ = 'notice'

    id = db.Column(db.Integer, primary_key=True)
    notice = db.Column(db.String(120), nullable=False)
    page_id = db.Column(db.Integer, db.ForeignKey('pages.id'))
    noticecontent = db.Column(db.String(120), nullable=False)


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    active = db.Column('is_active', db.Boolean(), nullable=False, server_default='1')
    # User authentication information. The collation='NOCASE' is required
    # to search case insensitively when USER_IFIND_MODE is 'nocase_collation'.
    username = db.Column(db.String(100, collation='NOCASE'), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False, server_default='')
    email_confirmed_at = db.Column(db.DateTime())
    # User information
    first_name = db.Column(db.String(100, collation='NOCASE'), nullable=False, server_default='')
    last_name = db.Column(db.String(100, collation='NOCASE'), nullable=False, server_default='')
    # Define the relationship to Role via UserRoles
    roles = db.relationship('Role', secondary='user_roles')
# Define the Role data-model
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(50), unique=True)
# Define the UserRoles association table
class UserRoles(db.Model):
    __tablename__ = 'user_roles'
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
    role_id = db.Column(db.Integer(), db.ForeignKey('roles.id', ondelete='CASCADE'))

    # Setup Flask-User and specify the User data-model
user_manager = UserManager(app, db, User)

    # Create all database tables
db.create_all()

    # Create 'member@example.com' user with no roles
if not User.query.filter(User.username == 'member').first():
    user = User(
        username='member',
        email_confirmed_at=datetime.datetime.utcnow(),
        password=user_manager.hash_passworddmin('Password1'),
    )
    db.session.add(user)
    db.session.commit()

    # Create 'admin@example.com' user with 'Admin' and 'Agent' roles
if not User.query.filter(User.username == 'droidthelast').first():
    user = User(
        username='droidthelast',
        email_confirmed_at=datetime.datetime.utcnow(),
        password=user_manager.hash_password('Password1'),
    )
    user.roles.append(Role(name='Admin'))
    user.roles.append(Role(name='Agent'))
    db.session.add(user)
    db.session.commit()

@app.route('/', methods=['POST', 'GET'])
def index():
	pages = Pages.query.all()
	return render_template('index.html', pages=pages)

@app.route('/post/<int:page_id>')
def post(page_id):
	page = Pages.query.filter_by(id=page_id).first()
	return render_template('single-post.html', id=page.id, category=page.category, title=page.title, content=page.content)

@app.route('/edit-page/<int:page_id>')
@login_required
def edit_page(page_id):
    page = Pages.query.filter_by(id=page_id).first()
    return render_template('edit-page.html', id=page.id, category=page.category, title=page.title, content=page.content)

@app.route('/update-page/', methods=['POST'])
@login_required
def update_page():
    page_id = request.form['id']
    category = request.form['category']
    title = request.form['title']
    content = request.form['content']
    Pages.query.filter_by(id=page_id).update({'title': title.encode('ascii'), 'category': category.encode('ascii'), 'content': content.encode('ascii')})
    db.session.commit()
    return redirect('/page/' + page_id)

@app.route('/save-page/', methods=['POST'])
@login_required
def save_page():
    page = Pages(title=request.form['title'].encode('ascii'), category=request.form['category'].encode('ascii'), content=request.form['content'].encode('ascii'))
    db.session.add(page)
    db.session.commit()
    return redirect('/page/%d' % page.id)

@app.route('/delete-page/<int:page_id>')
@login_required
def delete_page(page_id):
    db.session.query(Pages).filter_by(id=page_id).delete()
    db.session.commit()
    return redirect('/')

if __name__=='__main__':
	app.run(debug=True)