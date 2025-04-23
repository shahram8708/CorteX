from . import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask import current_app
import os

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    phone = db.Column(db.String(15))
    address = db.Column(db.String(200))
    user_type = db.Column(db.String(50))  

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class FoodPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    quantity = db.Column(db.String(50), nullable=False)
    expiry_timeline = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    pin_code = db.Column(db.String(10), nullable=False)
    image_filename = db.Column(db.String(200), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_paid = db.Column(db.Boolean, default=False)
    price = db.Column(db.String(50), nullable=True)
    donor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    donor = db.relationship('User', backref='food_posts')
    in_stock = db.Column(db.Boolean, default=True)

from enum import Enum

class RequestStatus(Enum):
    PENDING = "Pending"
    ACCEPTED = "Accepted"
    COMPLETED = "Completed"

class PickupRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    foodpost_id = db.Column(db.Integer, db.ForeignKey('food_post.id'), nullable=False)
    requesting_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=RequestStatus.PENDING.value)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    foodpost = db.relationship('FoodPost', backref='pickup_requests')
    requesting_user = db.relationship('User', backref='pickup_requests')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    request_id = db.Column(db.Integer, db.ForeignKey('pickup_request.id'), nullable=False)
    message_text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])
    request = db.relationship('PickupRequest', backref='messages')
