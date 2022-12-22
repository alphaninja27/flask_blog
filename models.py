from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager
from enum import unique
from datetime import datetime

db = SQLAlchemy()
login = LoginManager()

class Follow(db.Model):
    __tablename__ = 'follows'

    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'),primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'),primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class UserModel(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key = True)
    email = db.Column(db.String(100), unique = True)
    username = db.Column(db.String(100))
    password_hash = db.Column(db.String(250))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    followed = db.relationship('Follow', foreign_keys=[Follow.follower_id], backref=db.backref('follower', lazy='joined'), lazy='dynamic', cascade='all, delete-orphan')
    followers = db.relationship('Follow', foreign_keys=[Follow.followed_id], backref=db.backref('followed', lazy='joined'), lazy='dynamic', cascade='all, delete-orphan')

    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)
    
    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)
 
    def is_following(self, user):
        return self.followed.filter_by(followed_id=user.id).first() is not None
 
    def is_followed_by(self, user):
        return self.followers.filter_by(follower_id=user.id).first() is not None

class CategoryMaster(db.Model):
    category_id = db.Column(db.Integer, primary_key = True)
    category_name = db.Column(db.String, nullable = False)
    blogmodel = db.relationship('BlogModel', backref = 'categorymaster', lazy = True)

class BlogModel(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    category_id = db.Column(db.Integer, db.ForeignKey('category_master.category_id'), nullable = False)
    blog_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = False)
    blog_text = db.Column(db.Text, nullable = False)
    blog_creation_date = db.Column(db.DateTime)
    blog_read_count = db.Column(db.Integer, default = 0)
    blog_rating_count = db.Column(db.Integer, default = 0)

class Blogcomment(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    blog_id = db.Column(db.Integer, db.ForeignKey('blog_model.id'), nullable = True)
    blog_comment = db.Column(db.Text)
    comment_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = True)
    blog_rating = db.Column(db.Integer)
    blog_comment_date = db.Column(db.DateTime)



@login.user_loader
def load_user(id):
    return UserModel.query.get(int(id))