import datetime

from project import db
from datetime import timedelta
import datetime

class Tweet(db.Model):
    __tablename__ = 'tweets'

    tweet_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    tweet = db.Column(db.String, nullable=False)
    posted = db.Column(db.DateTime, nullable=False)
    poster = db.relationship("User", back_populates="tweets", passive_deletes=True)
    comments = db.relationship('Comment', back_populates='tweet', passive_deletes=True)
    likes = db.relationship('Like', back_populates='tweet', passive_deletes=True)

    def __init__(self, tweet, posted, user_id):
        self.tweet = tweet
        self.posted = posted
        self.user_id = user_id

    def __repr__(self):
        return '<Id {0} - {1}>'.format(self.tweet_id, self.tweet)


    @classmethod
    def delta_time(cls, tweet_posted):
        now = datetime.datetime.now()
        td = now - tweet_posted
        days = td.days
        hours = td.seconds//3600
        minutes = (td.seconds//60)%60
        if days > 0:
            return tweet_posted.strftime("%d %B, %Y")
        elif hours > 0:
            return str(hours) + 'h'
        elif minutes > 0:
            return str(minutes) + 'm'
        else:
            return 'few seconds ago'


class Comment(db.Model):
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    poster = db.relationship('User', back_populates='comments', passive_deletes=True)
    text = db.Column(db.String, nullable=False)
    posted = db.Column(db.DateTime, nullable=False)
    tweet_id = db.Column(db.Integer, db.ForeignKey('tweets.tweet_id', ondelete="CASCADE"), nullable=False)
    tweet = db.relationship('Tweet', back_populates='comments', passive_deletes=True)

    def __init__(self, text=None, user_id=None, posted=None, tweet_id=None):
        self.text = text
        self.user_id = user_id
        self.posted = posted
        self.tweet_id = tweet_id

    def __repr__(self):
        pass

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    jury = db.Column(db.String, nullable=False, default=False)
    tweets = db.relationship('Tweet', back_populates='poster')
    role = db.Column(db.String, default='user')
    comments = db.relationship('Comment', back_populates='poster', passive_deletes=True)
    changes = db.relationship('Change', back_populates='poster', passive_deletes=True)
    likes = db.relationship('Like', back_populates='liker', passive_deletes=True)
    discussion_comments = db.relationship('Discussion_Comment', back_populates='poster')
    replies = db.relationship('Reply', back_populates='poster', passive_deletes=True)

    def __init__(self, name=None, email=None, password=None, jury=None, role=None):
        self.name = name
        self.email = email
        self.password = password
        self.role = role
        self.jury = jury

    def __repr__(self):
        return '<User {0}>'.format(self.name)

    @classmethod
    def is_following(cls, who_id, whom_id):
        whom_ids = db.session.query(Follower.whom_id).filter_by(who_id=who_id).all()
        whom_ids = [i[0] for i in whom_ids]
        if whom_id in whom_ids:
            return True
        else:
            return False

class Like(db.Model):
    __tablename__ = 'likes'

    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    liker = db.relationship('User', back_populates='likes', passive_deletes=True)
    tweet_id = db.Column(db.Integer, db.ForeignKey('tweets.tweet_id', ondelete="CASCADE"), nullable=False)
    tweet = db.relationship('Tweet', back_populates='likes', passive_deletes=True)

class Change(db.Model):
    __tablename__ = 'changes'

    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    poster = db.relationship('User', back_populates='changes', passive_deletes=True)
    # likes = db.relationship('Like', back_populates='tweet', passive_deletes=True)

class Follower(db.Model):
    __tablename__ = 'follower'
    __table_args__ = (
        db.PrimaryKeyConstraint('who_id', 'whom_id'),
    )

    who_id = db.Column(db.Integer)
    whom_id = db.Column(db.Integer)


    def __init__(self, who_id, whom_id):
        self.who_id = who_id
        self.whom_id = whom_id

    def __repr__(self):
        return '<User {0} follows {1}>'.format(self.who_id, self.whom_id)

class Group(db.Model):
    __tablename__ = 'groups'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete="CASCADE"), primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey('issues.id', ondelete="CASCADE"))

    def __init__(self, user_id=None, issue_id=None):
        self.user_id = user_id
        self.issue_id = issue_id

    def __repr__(self):
        return str(self.issue_id)

class Issue(db.Model):
    __tablename__ = 'issues'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, unique=True, nullable=False)
    prompt = db.Column(db.String, unique=True, nullable=False)
    question = db.Column(db.String, nullable=False)
    type = db.Column(db.String, nullable=False, default=False)
    result = db.Column(db.String, default='In Progress')
    end_date = db.Column(db.DateTime, nullable=False)

    def __init__(self, title=None, prompt=None, question=None, type=None):
        self.title = title
        self.prompt = prompt
        self.question = question
        self.type = type
        self.end_date = datetime.datetime.now() + timedelta(days=10)

    def __repr__(self):
        return '<Issue {0} entitled {1}>'.format(self.id, self.title)

class Discussion_Comment(db.Model):
    __tablename__ = 'discussion_comments'

    comment_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    comment = db.Column(db.String, nullable=False)
    posted = db.Column(db.DateTime, nullable=False)
    archived = db.Column(db.String, nullable=False, default=False)
    poster = db.relationship("User", back_populates="discussion_comments", passive_deletes=True)
    replies = db.relationship('Reply', back_populates='disc_comment', passive_deletes=True)

    def __init__(self, comment=None, posted=None, user_id=None, archived=False):
        self.comment = comment
        self.posted = posted
        self.user_id = user_id
        self.archived = archived

    def __repr__(self):
        return '<Id {0} - {1}>'.format(self.tweet_id, self.tweet)

    @classmethod
    def delta_time(cls, comment_posted):
        now = datetime.datetime.now()
        td = now - comment_posted
        days = td.days
        hours = td.seconds//3600
        minutes = (td.seconds//60)%60
        if days > 0:
            return comment_posted.strftime("%d %B, %Y")
        elif hours > 0:
            return str(hours) + 'h'
        elif minutes > 0:
            return str(minutes) + 'm'
        else:
            return 'few seconds ago'

    @classmethod
    def delta_time(cls, tweet_posted):
        now = datetime.datetime.now()
        td = now - tweet_posted
        days = td.days
        hours = td.seconds//3600
        minutes = (td.seconds//60)%60
        if days > 0:
            return tweet_posted.strftime("%d %B, %Y")
        elif hours > 0:
            return str(hours) + 'h'
        elif minutes > 0:
            return str(minutes) + 'm'
        else:
            return 'few seconds ago'

class Reply(db.Model):
    __tablename__ = 'replies'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    poster = db.relationship('User', back_populates='replies', passive_deletes=True)
    text = db.Column(db.String, nullable=False)
    posted = db.Column(db.DateTime, nullable=False)
    reply_id = db.Column(db.Integer, db.ForeignKey('discussion_comments.comment_id', ondelete="CASCADE"), nullable=False)
    disc_comment = db.relationship('Discussion_Comment', back_populates='replies', passive_deletes=True)

    def __init__(self, text=None, user_id=None, posted=None, reply_id=None):
        self.text = text
        self.user_id = user_id
        self.posted = posted
        self.reply_id = reply_id

    def __repr__(self):
        pass
