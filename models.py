from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, UTC

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    datetime = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    performance = db.relationship('Performance', backref='user', lazy=True)
    resume = db.relationship('Resume', backref='user', lazy=True)

class Performance(db.Model):
    __tablename__ = 'performance'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class Resume(db.Model):
    __tablename__ = 'resume'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    resume_path = db.Column(db.String(256), nullable=False)
    datetime = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

class UserEmotionData(db.Model):
    __tablename__ = 'user_emotion_data'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    emotion = db.Column(db.String(20), nullable=False)
    confidence = db.Column(db.Float, nullable=False)

class SessionSummary(db.Model):
    __tablename__ = 'session_summary'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    summary_text = db.Column(db.Text, nullable=False)

