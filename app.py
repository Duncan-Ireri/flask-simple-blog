import datetime, os, random, string
from flask import Flask, request, render_template, session, url_for, redirect
from flask_babelex import Babel
from flask_sqlalchemy import SQLAlchemy
from flask_user import current_user, login_required, roles_required, UserManager, UserMixin, user_manager
from flask_uploads import UploadSet, configure_uploads, IMAGES, patch_request_class
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms.validators import DataRequired
from werkzeug.utils import secure_filename
from wtforms_sqlalchemy.fields import QuerySelectField
from wtf_tinymce.forms.fields import TinyMceField
from wtforms import SubmitField, StringField, PasswordField, TextAreaField
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
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
admin = Admin(app)
from wtf_tinymce import wtf_tinymce
wtf_tinymce.init_app(app)

# Define the User data-model.
# NB: Make sure to add flask_user UserMixin !!!

class Categories(db.Model):
    __tablename_ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(120), nullable=False)
    created = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __init__(self, category_name):
        self.category_name = category_name

    def __repr__(self):
        return '%r' % (self.category_name)


class Pages(db.Model):
    __tablename__ = 'pages'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.Integer, db.ForeignKey('categories.id'))
    title = db.Column(db.String(1000))
    content = db.Column(db.Text())
    page_created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    topic_name = db.Column(db.String(120), nullable=False)

    def __init__(self, title, content, topic_name, category):
        self.title = title
        self.content = content
        self.topic_name = topic_name
        self.category = category

    def __repr__(self):
        return '<Pages : id=%r, title=%s, content=%s>' % (self.id, self.title, self.content)

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

admin.add_view(ModelView(Categories, db.session))
admin.add_view(ModelView(Pages, db.session))
    # Create all database tables
db.create_all()

    # Create 'member@example.com' user with no roles
if not User.query.filter(User.username == 'member').first():
    user = User(
        username='member',
        email_confirmed_at=datetime.datetime.utcnow(),
        password=user_manager.hash_password('Password1'),
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

class CategoriesForm(FlaskForm):
    categories = StringField('Category', validators=[DataRequired()])
    submit = SubmitField(u'Update')

def cate_form():
    return Categories.query

class PagesForm(FlaskForm):
    categories = QuerySelectField('Categories', query_factory=cate_form, get_label='Categories', allow_blank=False)
    title = StringField('Title', validators=[DataRequired()])
    content = TinyMceField(
        'Content',
        tinymce_options={'toolbar': 'bold italic | link | code'}
    )
    topic = StringField('Topic', validators=[DataRequired()])
    submit = SubmitField(u'Upload')

@app.route('/', methods=['POST', 'GET'])
def index():
	pages = Pages.query.all()
	return render_template('index.html', pages=pages)


@app.route('/new_post/')
@login_required
@roles_required('Admin')
def new_post():
    form = PagesForm()
    return render_template('newpost.html', form=form)    

@app.route('/new_category/')
@login_required
@roles_required('Admin')
def new_category():
    form = CategoriesForm()
    return render_template('newcategory.html', form=form)    

@app.route('/post/<int:page_id>')
def post(page_id):
	page = Pages.query.filter_by(id=page_id).first()
	return render_template('single-post.html', id=page.id, category=page.category, title=page.title, page_created=page.page_created, content=page.content)

@app.route('/edit-page/<int:page_id>')
@login_required
def edit_page(page_id):
    page = Pages.query.filter_by(id=page_id).first()
    return render_template('edit.html', id=page.id, category=page.category, title=page.title, page_created=page.page_created, content=page.content)

@app.route('/update-post/', methods=['POST'])
@login_required
def update_post():
    page_id = request.form['id']
    category = request.form['category']
    title = request.form['title']
    content = request.form['content']
    page_created = request.form['page_created']
    Pages.query.filter_by(id=page_id).update({'title': title, 'category': category, 'page_created': page_created, 'content': content})
    db.session.commit()
    return redirect('/post/' + page_id)

@app.route('/save-post/', methods=['POST', 'GET'])
@login_required
@roles_required('Admin')
def save_post():
    form = PagesForm()
    page = Pages(title=form.title.data, category=form.categories.data, content=form.content.data, topic_name=form.topic.data)
    db.session.add(page)
    db.session.commit()
    return redirect('/post/%d' % page.id)

@app.route('/save_cat/', methods=['POST', 'GET'])
@login_required
@roles_required('Admin')
def save_cat():
    form = CategoriesForm()
    categ = Categories(category_name=form.categories.data)
    db.session.add(categ)
    db.session.commit()
    return redirect('/')

@app.route('/delete-page/<int:page_id>')
@login_required
def delete_page(page_id):
    db.session.query(Pages).filter_by(id=page_id).delete()
    db.session.commit()
    return redirect('/')

if __name__=='__main__':
	app.run(debug=True)