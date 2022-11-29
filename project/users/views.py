# imports
import datetime
from functools import wraps
from flask import (flash, redirect, render_template,
                   request, session, url_for, Blueprint)
from sqlalchemy.exc import IntegrityError

from .forms import RegisterForm, LoginForm, JuryForm, PostJuryForm, ScaleVoteForm, BinaryVoteForm, FeedbackVoteForm
from project import db, bcrypt
from project.models import User, Follower, Issue, Group, Discussion_Comment, Reply

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
    if issue_id is not None:
        issue = Issue.query.filter_by(id=issue_id).first()
        if issue.type == '0':
            vote_form = ScaleVoteForm(request.form)
        elif issue.type == '1':
            vote_form = BinaryVoteForm(request.form)
        elif issue.type == '2':
            vote_form = FeedbackVoteForm(request.form)
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
        current_user_id = session['user_id'], issue=issue, date=datetime.datetime.now()
    )

@users_blueprint.route('/discussion/delete/<int:disc_id>/')
@login_required
def delete_disc(disc_id):
    our_disc_id = disc_id
    disc_comment = db.session.query(Discussion_Comment).filter_by(comment_id=our_disc_id)
    if disc_comment.first():
        if session['user_id'] == disc_comment.first().user_id:
            disc_comment.delete()
            db.session.commit()
            flash('That comment was deleted.')
            return redirect(url_for('users.jury'))
        else:
            flash('You can only delete comments that belong to you.')
            return redirect(url_for('users.jury'))
    else:
        flash('That tweet does not exist. Saw what you did there, Hacker!')
        return redirect(url_for('users.jury'))

@users_blueprint.route('/create-reply/<comment_id>', methods=['POST'])
@login_required
def create_reply(comment_id):
    our_comment_id = comment_id
    text = request.form.get('text')

    if not text:
        flash('Reply cannot be empty', category='error')
    else:
        disc_comment = Discussion_Comment.query.filter_by(comment_id=our_comment_id)
        if disc_comment:
            reply = Reply(text,
                            session['user_id'],
                            datetime.datetime.now(),
                            our_comment_id)
            db.session.add(reply)
            db.session.commit()
        else:
            flash("Discussion comment does not exist", category='error')

    return redirect(url_for('users.jury'))

@users_blueprint.route("/delete-reply/<reply_id>")
@login_required
def delete_reply(reply_id):
    reply = Reply.query.filter_by(id=reply_id).first()

    if not reply:
        flash('Reply does not exist.', category='error')
    elif session['user_id'] != reply.user_id and session['user_id'] != reply.disc_comment.user_id:
        flash('You do not have permission to delete this reply.', category='error')
    else:
        db.session.delete(reply)
        db.session.commit()

    return redirect(url_for('users.jury'))

@users_blueprint.route('/closejury/<issue_id>', methods=['GET'])
@login_required
@admin_required
def close_jury(issue_id):
    if issue_id is not None:
        issue = Issue.query.filter_by(id=issue_id).first()
        if issue.result == "In Progress":
            try:
                member_ids = db.session.query(Group.user_id).filter_by(issue_id=issue_id)
                member_votes = db.session.query(Group.vote).filter_by(issue_id=issue_id)
                if issue.type == '0':
                    strongly_disagree, disagree, neutral, agree, strongly_agree, undecided_count = 0, 0, 0, 0, 0, 0
                    for vote in member_votes:
                        if vote[0] == '0':
                            strongly_disagree += 1
                        elif vote[0] == '1':
                            disagree += 1
                        elif vote[0] == '2':
                            neutral += 1
                        elif vote[0] == '3':
                            agree += 1
                        elif vote[0] == '4':
                            strongly_agree += 1
                        else:
                            undecided_count += 1
                    total_votes = strongly_disagree + disagree + neutral + agree + strongly_agree + undecided_count
                    result_string = "Strongly Disagree: {}% Disagree: {}% Neutral: {}% Agree: {}% Strongly Agree: {}% Undecided: {}%".format(
                        ((strongly_disagree/total_votes)*100), ((disagree/total_votes)*100), ((neutral/total_votes)*100), 
                        ((agree/total_votes)*100), ((strongly_agree/total_votes)*100), ((undecided_count/total_votes)*100))
                    db.session.query(Issue).filter_by(id=issue_id).update({'result': result_string})
                    db.session.commit()
                elif issue.type == '1':
                    no_count = 0
                    yes_count = 0
                    undecided_count = 0
                    for vote in member_votes:
                        if vote[0] == '0':
                            no_count += 1
                        elif vote[0] == '1':
                            yes_count += 1
                        else:
                            undecided_count += 1
                    total_votes = no_count + yes_count + undecided_count
                    result_string = "No Votes: {}% Yes Votes: {}% Undecided Votes: {}%".format(((no_count/total_votes)*100), ((yes_count/total_votes)*100), ((undecided_count/total_votes)*100))
                    db.session.query(Issue).filter_by(id=issue_id).update({'result': result_string})
                    db.session.commit()
                elif issue.type == '2':
                    db.session.query(Issue).filter_by(id=issue_id).update({'result': "Feedback closed"})
                    db.session.commit()
                else:
                    db.session.query(Issue).filter_by(id=issue_id).update({'result': "Closed"})
                    db.session.commit()
                if member_ids.all():
                    discussion_comments = db.session.query(Discussion_Comment).filter(Discussion_Comment.user_id.in_(member_ids))
                    for comment in discussion_comments:
                        comment.archived = True
                    db.session.commit()
                db.session.query(Group).filter_by(issue_id=issue_id).update({'issue_id': None, 'vote': 'Undecided'})
                db.session.commit()
                flash('The jury issue has been closed.')
            except:
                flash('Jury issue was not able to be closed.', category='error')
        else: 
            flash('Jury issue is already closed.', category='error')
    else: 
        flash('Jury issue does not exist.', category='error')
    return redirect(url_for('users.admin'))
