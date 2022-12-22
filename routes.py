from datetime import date, datetime
from flask import Flask, render_template, redirect, request, url_for, flash
from flask_login import login_required, current_user, login_user, logout_user
from models import BlogModel, Blogcomment, CategoryMaster, UserModel, Follow, db, login
from sqlalchemy import func
from werkzeug.utils import secure_filename
import urllib.request
import os
import sqlite3

global_all_category_no = None
global_all_category_name = None

app = Flask(__name__)
app.secret_key = 'alphaninja27'

UPLOAD_FOLDER = 'static/uploads/'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATION'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db.init_app(app)
login.init_app(app)

login.login_view = 'login'

def get_all_categories():
    global global_all_category_no, global_all_category_name
    all_category_info = db.session.query(CategoryMaster.category_id, CategoryMaster.category_name)
    all_category_info = list(all_category_info)

    global_all_category_no, global_all_category_name = zip(*all_category_info)

@app.before_first_request
def create_all():
    db.create_all()
    get_all_categories()

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/blogs')
    if request.method == 'POST':
        email = request.form.get('email')
        user = UserModel.query.filter_by(email = email).first()
        if user is not None and user.check_password(request.form.get('password')):
            login_user(user)
            return redirect('/blogs')
        return render_template('/register.html')
    return render_template('/login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect('/register')

@app.route('/register', methods = ['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect('/blogs')
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')

        if UserModel.query.filter_by(email=email).first():
            return "Email Already Exists"

        user = UserModel(email=email,username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return redirect('/blogs')
    return render_template('register.html')

@app.route('/blogs')
def blogs():
    if current_user.is_authenticated:
        return render_template('/blogs_home.html')
    return redirect(url_for('list_all_blogs'))

@app.route('/createBlog', methods = ["GET", "POST"])
@login_required
def create_blog():
    if request.method == 'POST':
        category_id = request.form.get('category_id')
        blog_text = request.form.get('blog_text')
        today = datetime.now()
        blog_user_id = current_user.id 
        blog_read_count = 0
        blog_rating_count = 0

        newBlog = BlogModel(category_id = category_id, blog_user_id = blog_user_id, blog_text = blog_text, blog_creation_date = today, blog_read_count = blog_read_count, blog_rating_count = blog_rating_count)
        db.session.add(newBlog)
        db.session.commit()
        return redirect('/blogs')
    else:
        return render_template('create_blog.html', all_category_id = global_all_category_no, all_category_name = global_all_category_name)
def upload_image():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No image selected for uploading')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        flash('Image successfully uploaded and displayed')
        return render_template('create_blog.html', filename = filename)
    else:
        flash('Allowed image types are - png, jpg, jpeg')
        return redirect(request.url)

@app.route('/display/<filename>')
def display_image(filename):
    return redirect(url_for('static', filename = 'uploads/' + filename), code = 301)

@app.route('/viewBlog')
@login_required
def view_blogs():
    all_self_blogs = BlogModel.query.filter(BlogModel.blog_user_id == current_user.id).all()
    return render_template('view_blog.html', all_self_blogs = all_self_blogs, all_categories = global_all_category_name)

@app.route('/self_blog_detail/<int:blog_model_id>/<string:blog_model_category>', methods = ['GET', 'POST'])
@login_required
def self_blog_detail(blog_model_id, blog_model_category):
    blog_model = BlogModel.query.get(blog_model_id)
    if request.method == 'POST':
        if request.form['action'] == 'Update':
            blog_model.blog_text = request.form.get('blog_text')
        else:
            BlogModel.query.filter_by(id = blog_model_id).delete()
        db.session.commit()
        return redirect('/viewBlog')
    return render_template('/self_blog_detail.html', blog_id = blog_model_id, blog_categories = blog_model_category, blog_text = blog_model.blog_text)

@app.route('/listAllBlogs')
def list_all_blogs():
    all_blogs = BlogModel.query.all()
    all_users = UserModel.query.all()
    return render_template('list_all_blogs.html', all_blogs = all_blogs, all_users = all_users, all_categories = global_all_category_name)

@app.route('/blogDetail/<int:blog_id>/<string:username>/<string:category>', methods = ['GET', 'POST'])
@login_required
def blog_detial(blog_id, username, category):
    blog = BlogModel.query.get(blog_id)
    if request.method == 'GET':
        if current_user.id != blog.blog_user_id:
            blog.blog_read_count = blog.blog_read_count + 1
            db.session.commit()
        rating = db.session.query(func.avg(Blogcomment.blog_rating)).filter(Blogcomment.blog_id == int(blog_id)).first()[0]
        return render_template('/blog_detail.html', blog = blog, rating = rating, author = username, category = category)
    else:
        rate = request.form.get('rating')
        comment = request.form.get('comment')
        blog_id = request.form.get('blog_id')
        oldComment = Blogcomment.query.filter(Blogcomment.blog_id == blog_id).filter(Blogcomment.comment_user_id == current_user.id).first()
        today = datetime.now()

        if oldComment == None:
            blog.blog_rating_count = blog.blog_rating_count + 1
            newComment = Blogcomment(
                blog_id = blog_id,
                comment_user_id = current_user.id,
                blog_comment = comment,
                blog_rating = rate,
                blog_comment_date = today
            )
            db.session.add(newComment)
        else:
            oldComment.blog_comment = comment
            oldComment.blog_rating = rate
        db.session.commit()
        return redirect('/blogs')

@app.route('/user/<string:username>')
def user(username):
 user = UserModel.query.filter_by(username=username).first()
 if user is None:
    os.abort(404)
 return render_template('/user.html', user=user)

@app.route('/follow/<string:username>')
@login_required
def follow(username):
    user = UserModel.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if current_user.is_following(user):
        flash('You are already following this user.')
        return redirect(url_for('.user', username=username))
    current_user.follow(user)
    flash('You are now following %s.' % username)
    return redirect(url_for('.user', username=username))

@app.route('/followers/<string:username>')
def followers(username):
    user = UserModel.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(page, per_page=app.config['FLASKY_FOLLOWERS_PER_PAGE'],error_out=False)
    follows = [{'user': item.follower, 'timestamp': item.timestamp} for item in pagination.items]
    return render_template('followers.html', user=user, title="Followers of", endpoint='.followers', pagination=pagination, follows=follows)


@app.route('/')
def home():
    return render_template('blogs_home.html')

if __name__ == '__main__':
    app.run(debug = True)