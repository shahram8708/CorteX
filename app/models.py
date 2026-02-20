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
    bank_account_holder = db.Column(db.String(100))
    bank_name = db.Column(db.String(100))
    account_number = db.Column(db.String(30))
    ifsc_code = db.Column(db.String(15))
    upi_id = db.Column(db.String(50))
    pan_number = db.Column(db.String(10))
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
    in_stock = db.Column(db.Boolean, default=True)
    donor = db.relationship('User', backref='food_posts')

from enum import Enum

class RequestStatus(Enum):
    PENDING = 'Payment Successful'
    ACCEPTED = 'Accepted'
    DELIVERY_ASSIGNED = 'Delivery Assigned'
    ARRIVED = 'Arrived'
    COMPLETED = 'Completed'
    REJECTED = 'Rejected'

class PickupRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    foodpost_id = db.Column(db.Integer, db.ForeignKey('food_post.id'), nullable=False)
    
    requesting_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    donor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    delivery_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    status = db.Column(db.String(50), default="Pending")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    delivery_otp = db.Column(db.String(6), nullable=True)
    requester_otp = db.Column(db.String(6), nullable=True)
    city = db.Column(db.String(100))

    # New fields for payment details
    paid_amount = db.Column(db.Float, nullable=True)
    payment_id = db.Column(db.String(100), nullable=True)
    payment_timestamp = db.Column(db.DateTime, nullable=True)
    refund_status = db.Column(db.String(20), default="not_refunded")
    donor = db.relationship('User', foreign_keys=[donor_id], backref='pickup_requests_received')
    foodpost = db.relationship('FoodPost', backref='pickup_requests')
    requesting_user = db.relationship('User', foreign_keys=[requesting_user_id], backref='pickup_requests_made')
    delivery_user = db.relationship('User', foreign_keys=[delivery_user_id], backref='deliveries_assigned')

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
