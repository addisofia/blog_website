import os
from dotenv import load_dotenv
from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
# Import your forms from the forms.py
from forms import CreatePostForm,RegisterForm,LoginForm,CommentForm


'''
Make sure the required packages are installed: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from the requirements.txt for this project.
'''
load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('Flask_Key')
ckeditor = CKEditor(app)
bootstrap = Bootstrap(app)

# TODO: Configure Flask-Login
login_manager=LoginManager()
login_manager.init_app(app)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# CREATE DATABASE
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI","sqlite:///posts.db")
db = SQLAlchemy(model_class=Base)
db.init_app(app)

#todo:config de la fonction decorateur admin_only
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Si user pas connecté → accès interdit
        if not current_user.is_authenticated:
            return abort(403)

        # Si user n'est pas admin → accès interdit
        if current_user.id != 1:   # ID du compte admin
            return abort(403)

        # Sinon exécuter la fonction
        return f(*args, **kwargs)
    return decorated_function


# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id:Mapped[int]=mapped_column(Integer,db.ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    author: Mapped["User"] = relationship("User", back_populates="posts")
    comments:Mapped[list["Comment"]]=relationship("Comment",back_populates="posts",cascade="all, delete")


# TODO: Create a User table for all your registered user.
class User(db.Model,UserMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(1000))
    name: Mapped[str] = mapped_column(String(1000))
    posts:Mapped[list["BlogPost"]]=relationship("BlogPost",back_populates="author")
    comments:Mapped[list["Comment"]]=relationship("Comment",back_populates="author")

class Comment(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id:Mapped[int]=mapped_column(Integer,db.ForeignKey("users.id"))
    post_id:Mapped[int]=mapped_column(Integer,db.ForeignKey("blog_posts.id"))
    body:Mapped[str] = mapped_column(String(250), nullable=False)
    author: Mapped["User"] = relationship("User", back_populates="comments")
    posts:Mapped["BlogPost"]=relationship("BlogPost", back_populates="comments")

with app.app_context():
    db.create_all()


# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register',methods=['POST','GET'])
def register():
    form=RegisterForm()
    if form.validate_on_submit():
        name=form.name.data
        email=form.email.data
        existing_user = db.session.execute(db.select(User).where(User.email == email)).scalar()
        if existing_user:
            flash("you're already registred, try to login !")
            return redirect(url_for('login'))

        pass_hash=generate_password_hash(form.password.data, method='pbkdf2:sha256',salt_length=8)
        new_user=User(email=email,password=pass_hash,name=name)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)

        return redirect(url_for('get_all_posts'))

    return render_template("register.html",form=form)


# TODO: Retrieve a user from the database based on their email. 
@app.route('/login',methods=['POST','GET'])
def login():
    form=LoginForm()

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        """existing_user= db.session.execute(db.select(User).where(User.email==form.email.data)).scalar()"""
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password,password):
            login_user(user)
            return redirect(url_for('get_all_posts'))
        else:
            flash("incorrect password try again!")
            return redirect(url_for('login'))

    return render_template("login.html",form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts)


# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>",methods=['POST','GET'])
def show_post(post_id):
    form = CommentForm()
    requested_post = db.get_or_404(BlogPost, post_id)
   # all_comments = db.session.execute(db.select(Comment)).scalar()
    all_comments=Comment.query.filter_by(post_id=post_id).all()
    if form.validate_on_submit():
      if not  current_user.is_authenticated:
          flash("you are not connected")
          return redirect(url_for("login"))

      new_comment=Comment(author_id=current_user.id,post_id=post_id,body=form.body.data)
      db.session.add(new_comment)
      db.session.commit()
      return redirect(url_for("show_post", post_id=post_id))


    return render_template("post.html", post=requested_post,all_comments=all_comments,form=form)


# TODO: Use a decorator so only an admin user can create a new post

@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


# TODO: Use a decorator so only an admin user can edit a post

@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True)


# TODO: Use a decorator so only an admin user can delete a post
@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=False)
