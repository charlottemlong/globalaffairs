# imports
import datetime
from functools import wraps
from flask import (flash, redirect, render_template,
                   request, session, url_for, Blueprint, jsonify)
from sqlalchemy.exc import IntegrityError

from .forms import RegisterForm, LoginForm, JuryForm, PostJuryForm, ScaleVoteForm, BinaryVoteForm, FeedbackVoteForm
from project import db, bcrypt
from project.models import User, Follower, Issue, Group, Discussion_Comment, Reply, Change, Upvote, Downvote

# config
users_blueprint = Blueprint('users', __name__)

# helper functions

def login_required(test):
    @wraps(test)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return test(*args, **kwargs)
        else:
            flash('You need to login first')
            return (redirect(url_for('users.login')))
    return wrap

def admin_required(test):
    @wraps(test)
    def wrap(*args, **kwargs):
        if 'admin' == session.get('role'):
            return test(*args, **kwargs)
        else:
            flash('You need to be an administrator to access this page.')
            return (redirect(url_for('users.login')))
    return wrap


# routes

@users_blueprint.route('/logout/')
@login_required
def logout():
    session.pop('logged_in', None)
    session.pop('user_id', None)
    session.pop('name', None)
    session.pop('role', None)
    flash('You have been logged out')
    return redirect(url_for('users.login'))

@users_blueprint.route('/', methods=['GET', 'POST'])
def login():
    error = None
    form = LoginForm(request.form)
    if request.method == 'POST':
        if form.validate():
            user = User.query.filter_by(name=request.form['name']).first()
            if user is not None and bcrypt.check_password_hash(user.password,
                                                               request.form['password']):
                session['logged_in'] = True
                session['user_id'] = user.id
                session['name'] = user.name
                session['role'] = user.role
                session['jury'] = user.jury
                flash('Welcome')
                return render_template('index.html')
            else:
                error = 'Invalid username or password.'
    return render_template('index.html', form=form, error=error)


@users_blueprint.route('/register/', methods=['GET', 'POST'])
def register():
    error = None
    form = RegisterForm(request.form)
    if 'logged_in' in session:
        return redirect(url_for('tweets.tweet'))
    if request.method == 'POST':
        if form.validate():
            new_user = User(
                form.name.data,
                form.email.data,
                bcrypt.generate_password_hash(form.password.data),
                form.jury.data
            )
            try:
                db.session.add(new_user)
                db.session.flush()
                if form.jury.data == 1:
                    add_group = Group(new_user.id, None)
                    db.session.add(add_group)
                db.session.commit()
                flash('Thanks for registering. Plese login.')
                return redirect(url_for('users.login'))
            except IntegrityError:
                error = 'That username and/or email already exists.'
                return render_template('register.html', form=form, error=error)
    return render_template('register.html', form=form, error=error)


@users_blueprint.route('/users/all_users')
@login_required
def all_users():
    users = db.session.query(User).all()
    return render_template('users.html', users=users)


@users_blueprint.route('/users/followers')
@login_required
def followers():
    users = db.session.query(User).all()
    return render_template('followers.html', users=users)


@users_blueprint.route('/about', methods=['GET'])
def about():
    error = None
    return render_template('about.html', error=error)
    
@users_blueprint.route("/upvote-change/<change_id>", methods=['POST'])
@login_required
def upvote(change_id):
    change = Change.query.filter_by(id=change_id).first()
    upvote = Upvote.query.filter_by(user_id=session['user_id'], id=change_id).first()
    downvote = Downvote.query.filter_by(user_id=session['user_id'], id=change_id).first()

    if not change:
        return jsonify({'error': 'Change does not exist.'}, 400)
    elif upvote: # we already have an upvote, so user is trying to remove upvote
        db.session.delete(upvote)
        db.session.commit()
    else:
        if downvote: # if previously he had a downvote we gotta remove it
            db.session.delete(downvote)
            db.session.commit()

        upvote = Upvote(user_id=session['user_id'], change_id=change_id, date_created=datetime.datetime.now())
        db.session.add(upvote)
        db.session.commit()

    return jsonify(
        {"upvotes": len(change.upvotes), 
         "upvoted": session['user_id'] in map(lambda x: x.user_id, change.upvotes),
         "downvotes": len(change.downvotes)
        }
    )

@users_blueprint.route("/downvote-change/<change_id>", methods=['POST'])
@login_required
def downvote(change_id):
    change = Change.query.filter_by(id=change_id).first()
    downvote = Downvote.query.filter_by(user_id=session['user_id'], id=change_id).first()
    upvote = Upvote.query.filter_by(user_id=session['user_id'], id=change_id).first()

    if not change:
        return jsonify({'error': 'Change does not exist.'}, 400)
    elif downvote: # we already have an downvote, so user is trying to remove upvote
        db.session.delete(downvote)
        db.session.commit()
    else:
        if upvote:
            db.session.delete(upvote)
            db.session.commit()

        downvote = Downvote(user_id=session['user_id'], change_id=change_id, date_created=datetime.datetime.now())
        db.session.add(downvote)
        db.session.commit()

    return jsonify(
        {
            "downvotes": len(change.downvotes),
            "downvoted": session['user_id'] in map(lambda x: x.user_id, change.downvotes),
            "upvotes": len(change.upvotes)
        }
    )


def make_group(issue_id):
    # Creates a group of users for jury duty task
    group_size = 2
    current_size = 0
    while current_size < group_size:
        member = Group.query.filter_by(issue_id=None).first()
        member.issue_id = issue_id
        current_size += 1


@users_blueprint.route('/admin', methods=['GET', 'POST'])
@login_required
@admin_required
def admin():
    error = None
    form = JuryForm(request.form)
    issues = db.session.query(Issue).all()
    if request.method == 'POST':
        if form.validate():
            new_issue = Issue(
                form.title.data,
                form.prompts.data,
                form.question.data,
                form.vote.data
            )
            try:
                db.session.add(new_issue)
                db.session.flush()
                make_group(new_issue.id)
                db.session.commit()
                flash('You successfully created a new issue')
                return redirect(url_for('users.admin'))
            except IntegrityError:
                error = 'Make sure all fields are filled in'
                return render_template('admin.html', form=form, error=error)
            except: 
                error = 'Not enough users to fulfill jury'
                return render_template('admin.html', form=form, error=error)
    return render_template('admin.html', form=form, error=error, issues=issues)

def filtered_comments(user_id):

    group = Group.query.filter_by(user_id=user_id).first()
    member_ids = db.session.query(
        Group.user_id).filter_by(issue_id=group.issue_id)
    user_comments = db.session.query(
        Discussion_Comment).filter_by(user_id=user_id).filter_by(archived=0)
    if member_ids.all():
        member_comments = db.session.query(Discussion_Comment).filter(
            Discussion_Comment.user_id.in_(member_ids)).filter(Discussion_Comment.archived==0)
        result = user_comments.union(member_comments)
        return result.order_by(Discussion_Comment.posted.desc())
    else:
        return user_comments.order_by(Discussion_Comment.posted.desc())

@users_blueprint.route('/jury', methods=['GET', 'POST'])
@login_required
def jury():
    member = Group.query.filter_by(user_id=session['user_id']).first()
    issue_id = member.issue_id
    vote = member.vote
    if issue_id is not None and vote == "Undecided":
        issue = Issue.query.filter_by(id=issue_id).first()
        if issue.type == '0':
            vote_form = ScaleVoteForm(request.form)
        elif issue.type == '1':
            vote_form = BinaryVoteForm(request.form)
        elif issue.type == '2':
            vote_form = None
        else:
            flash('Invalid feedback type.', category='error')
            vote_form = None
            
    else: 
        issue = None
        vote_form = None

    if request.method == 'POST':
        if vote_form.validate():
            try:
                db.session.query(Group).filter_by(user_id=session['user_id']).update({'vote': vote_form.vote.data})
                db.session.commit()
                flash('You successfully voted. Thank you for your participation in the jury!')
                return redirect(url_for('users.jury'))
            except IntegrityError:
                error = 'Make sure to vote before submitting'
                return redirect(url_for('users.jury'))

    return render_template(
        'jury.html',
        form=PostJuryForm(),
        all_comments=filtered_comments(session['user_id']),
        current_user_id = session['user_id'], issue=issue, date=datetime.datetime.now(),
        vote_form = vote_form
    )

@users_blueprint.route('/jury/post', methods=['GET', 'POST'])
@login_required
def post_discussion():
    member = Group.query.filter_by(user_id=session['user_id']).first()
    issue_id = member.issue_id
    if issue_id is not None:
        issue = Issue.query.filter_by(id=issue_id).first()
    else: 
        issue = None
    error = None
    form = PostJuryForm()
    if request.method == 'POST':
        if form.validate():
            new_discuss_comment = Discussion_Comment(
                form.comment.data,
                datetime.datetime.now(),
                session['user_id'],
                False, issue_id
            )
            db.session.add(new_discuss_comment)
            db.session.commit()
            flash('Discussion comment has been posted.')
            return redirect(url_for('users.jury'))
    return render_template(
        'jury.html',
        form=form,
        error=error,
        all_comments=filtered_comments(session['user_id']),
        current_user_id = session['user_id'], 
        issue=issue
)
