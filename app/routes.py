from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session, abort
from .forms import RegistrationForm, LoginForm, FoodPostForm, OTPForm, ProfileEditForm
from .models import db, User, FoodPost, PickupRequest, RequestStatus, Message
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import os
from collections import defaultdict
from sqlalchemy.sql import func
from datetime import datetime
import random
from flask_mail import Message
import time
from . import db, mail
from werkzeug.security import generate_password_hash


def get_month_labels():
    return ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
            'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

main = Blueprint('main', __name__)

@main.route('/')
def home():
    return render_template('home.html')

@main.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '')  
    results = []

    if query:
        
        results = FoodPost.query.filter(
            (FoodPost.item_name.ilike(f'%{query}%')) | 
            (FoodPost.description.ilike(f'%{query}%')) |
            (FoodPost.city.ilike(f'%{query}%'))
        ).all()

    return render_template('search_results.html', posts=results)

def send_otp_email(email, otp):
    msg = Message("Your OTP for CorteX Registration", recipients=[email])
    msg.body = f"Your OTP for registration is: {otp}"
    mail.send(msg)

@main.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    
    if form.validate_on_submit():
        
        session['reg_data'] = {
            'name':         form.name.data,
            'email':        form.email.data,
            'phone':        form.phone.data,
            'address':      form.address.data,
            'user_type':    form.user_type.data,
            
            'password_hash': generate_password_hash(form.password.data)
        }

        
        otp = random.randint(100000, 999999)
        session['otp'] = otp
        session['otp_expiry'] = time.time() + 300

        
        send_otp_email(form.email.data, otp)

        flash('An OTP has been sent to your email. Please enter it to verify your account.', 'info')
        return redirect(url_for('main.verify_otp', email=form.email.data))

    
    return render_template('register.html', form=form)

@main.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    email = request.args.get('email')
    otp_form = OTPForm()
    
    if otp_form.validate_on_submit():
        
        if 'otp' not in session or time.time() > session.get('otp_expiry'):
            flash('OTP expired. Please try again.', 'danger')
            return redirect(url_for('main.register'))

        if otp_form.otp.data == str(session['otp']):
            
            reg = session.get('reg_data', {})
            if not reg:
                flash('Session expired. Please register again.', 'danger')
                return redirect(url_for('main.register'))

            
            user = User(
                name       = reg['name'],
                email      = reg['email'],
                phone      = reg['phone'],
                address    = reg['address'],
                user_type  = reg['user_type']
            )
            
            user.password_hash = reg['password_hash']

            db.session.add(user)
            db.session.commit()

            
            for key in ('reg_data', 'otp', 'otp_expiry'):
                session.pop(key, None)

            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('main.login'))
        else:
            flash('Invalid OTP. Please try again.', 'danger')

    return render_template('verify_otp.html', email=email, form=otp_form)

@main.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            
            
            send_login_email(user.email)
            
            
            dashboard = f"{user.user_type}_dashboard"
            return redirect(url_for(f"main.{dashboard}"))
        flash('Invalid email or password', 'danger')
    return render_template('login.html', form=form)

def send_login_email(user_email):
    msg = Message("Successful Login Notification",
                  recipients=[user_email])
    msg.body = "Dear user, you have successfully logged into your CorteX account."
    mail.send(msg)

@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.login'))

@main.route('/restaurant_dashboard')
@login_required
def restaurant_dashboard():
    if current_user.user_type != 'restaurant':
        return redirect(url_for('main.home'))
    
    food_posts = FoodPost.query.filter_by(donor_id=current_user.id).all()
    completed_requests = PickupRequest.query \
        .join(FoodPost).filter(
            FoodPost.donor_id == current_user.id,
            PickupRequest.status == "Completed"
        ).count()

    monthly_data = defaultdict(int)
    for post in food_posts:
        month = post.timestamp.month
        monthly_data[month] += 1  

    
    total_food_saved_kg = len(food_posts) * 2

    return render_template(
        'dashboards/restaurant_dashboard.html',
        user=current_user,
        total_posts=len(food_posts),
        completed_requests=completed_requests,
        food_saved=total_food_saved_kg,
        chart_labels=get_month_labels(),
        chart_data=[monthly_data.get(m, 0) for m in range(1, 13)]
    )

@main.route('/ngo_dashboard')
@login_required
def ngo_dashboard():
    if current_user.user_type != 'ngo':
        return redirect(url_for('main.home'))
    requests = PickupRequest.query.filter_by(requesting_user_id=current_user.id).all()
    completed = [r for r in requests if r.status == "Completed"]
    unique_donors = set(r.foodpost.donor_id for r in completed)

    
    daily_counts = defaultdict(int)
    for req in requests:
        day = req.timestamp.strftime('%Y-%m-%d')
        daily_counts[day] += 1

    return render_template(
        'dashboards/ngo_dashboard.html',
        user=current_user,
        total_requests=len(requests),
        total_completed=len(completed),
        unique_donors=len(unique_donors),
        chart_labels=list(daily_counts.keys()),
        chart_data=list(daily_counts.values())
    )

@main.route('/donor_dashboard')
@login_required
def donor_dashboard():
    if current_user.user_type != 'donor':
        return redirect(url_for('main.home'))
    food_posts = FoodPost.query.filter_by(donor_id=current_user.id).all()
    completed_requests = PickupRequest.query \
        .join(FoodPost).filter(
            FoodPost.donor_id == current_user.id,
            PickupRequest.status == "Completed"
        ).count()

    
    monthly_data = defaultdict(int)
    for post in food_posts:
        month = post.timestamp.month
        monthly_data[month] += 1  

    total_food_saved_kg = len(food_posts) * 2  

    return render_template(
        'dashboards/donor_dashboard.html',
        user=current_user,
        total_posts=len(food_posts),
        completed_requests=completed_requests,
        food_saved=total_food_saved_kg,
        chart_labels=get_month_labels(),
        chart_data=[monthly_data.get(m, 0) for m in range(1, 13)]
    )

@main.route('/beneficiary_dashboard')
@login_required
def beneficiary_dashboard():
    if current_user.user_type != 'beneficiary':
        return redirect(url_for('main.home'))
    requests = PickupRequest.query.filter_by(requesting_user_id=current_user.id).all()
    completed = [r for r in requests if r.status == "Completed"]
    unique_donors = set(r.foodpost.donor_id for r in completed)

    
    daily_counts = defaultdict(int)
    for req in requests:
        day = req.timestamp.strftime('%Y-%m-%d')
        daily_counts[day] += 1

    return render_template(
        'dashboards/beneficiary_dashboard.html',
        user=current_user,
        total_requests=len(requests),
        total_completed=len(completed),
        unique_donors=len(unique_donors),
        chart_labels=list(daily_counts.keys()),
        chart_data=list(daily_counts.values())
    )

ALLOWED_USER_TYPES = ['restaurant', 'donor']
REQUESTER_USER_TYPES = ['ngo', 'beneficiary']

def save_image(image):
    filename = secure_filename(image.filename)
    upload_path = os.path.join(current_app.root_path, 'static', 'uploads', filename)
    image.save(upload_path)
    return filename

@main.route('/post_food', methods=['GET', 'POST'])
@login_required
def post_food():
    if current_user.user_type not in ALLOWED_USER_TYPES:
        flash("Only Restaurants and Donors can post food.", "warning")
        return redirect(url_for("main.login"))
    
    form = FoodPostForm()
    if form.validate_on_submit():
        image_filename = None
        if form.image.data:
            image_filename = save_image(form.image.data)

        food = FoodPost(
            item_name=form.item_name.data,
            description=form.description.data,
            quantity=form.quantity.data,
            expiry_timeline=form.expiry_timeline.data,
            city=form.city.data,
            pin_code=form.pin_code.data,
            is_paid=form.is_paid.data,
            price=form.price.data if form.is_paid.data else None,
            image_filename=image_filename,
            donor=current_user,
            in_stock=True
        )
        db.session.add(food)
        db.session.commit()
        flash("Food posted successfully!", "success")
        return redirect(url_for('main.listing_detail', post_id=food.id))

    return render_template('post_food.html', form=form)

@main.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@main.route('/about')
def about():
    return render_template('about.html')

@main.route('/terms')
def terms():
    return render_template('terms.html')

@main.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy-policy.html')

@main.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = ProfileEditForm(obj=current_user)  
    
    if form.validate_on_submit():
        
        current_user.name = form.name.data
        current_user.email = form.email.data
        current_user.phone = form.phone.data
        current_user.address = form.address.data

        
        if form.password.data:
            current_user.set_password(form.password.data)

        db.session.commit()  
        
        flash("Your profile has been updated successfully!", "success")
        return redirect(url_for('main.profile'))

    return render_template('edit_profile.html', form=form)

@main.route('/delete_food/<int:post_id>', methods=['POST'])
@login_required
def delete_food(post_id):
    food_post = FoodPost.query.get_or_404(post_id)

    
    if food_post.donor_id != current_user.id:
        flash("Unauthorized access", "danger")
        return redirect(url_for('main.my_listings'))

    
    PickupRequest.query.filter_by(foodpost_id=post_id).delete()

    
    

    
    db.session.commit()

    
    db.session.delete(food_post)
    db.session.commit()

    flash("Food listing deleted successfully!", "success")
    return redirect(url_for('main.my_listings'))

@main.route('/listing/<int:post_id>')
def listing_detail(post_id):
    post = FoodPost.query.get_or_404(post_id)

    user_request = None
    if current_user.is_authenticated:
        user_request = PickupRequest.query.filter_by(
            requesting_user_id=current_user.id,
            foodpost_id=post_id
        ).first()

    return render_template('listing_detail.html', post=post, user_request=user_request)

@main.route('/mark_out_of_stock/<int:post_id>', methods=['POST'])
@login_required
def mark_out_of_stock(post_id):
    post = FoodPost.query.get_or_404(post_id)
    if post.donor_id != current_user.id:
        abort(403)
    post.in_stock = False  
    db.session.commit()
    flash("Marked as out of stock.", "info")
    return redirect(url_for('main.listing_detail', post_id=post.id))

@main.route('/mark_in_stock/<int:post_id>', methods=['POST'])
@login_required
def mark_in_stock(post_id):
    post = FoodPost.query.get_or_404(post_id)
    if post.donor_id != current_user.id:
        abort(403)
    post.in_stock = True  
    db.session.commit()
    flash("Marked as in stock.", "success")
    return redirect(url_for('main.listing_detail', post_id=post.id))

@main.route('/edit_food/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_food(post_id):
    food = FoodPost.query.get_or_404(post_id)

    
    if food.donor_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('main.listing_detail', post_id=post_id))

    form = FoodPostForm(obj=food)  

    
    food.in_stock = food.in_stock  

    if form.validate_on_submit():
        food.item_name = form.item_name.data
        food.description = form.description.data
        food.quantity = form.quantity.data
        food.expiry_timeline = form.expiry_timeline.data
        food.city = form.city.data
        food.pin_code = form.pin_code.data
        food.is_paid = form.is_paid.data
        food.price = form.price.data if form.is_paid.data else None
        
        if form.image.data:
            food.image_filename = save_image(form.image.data)

        db.session.commit()
        flash("Food listing updated!", "success")
        return redirect(url_for('main.listing_detail', post_id=post_id))

    return render_template('post_food.html', form=form, edit_mode=True)

@main.route('/my_listings')
@login_required
def my_listings():
    posts = FoodPost.query.filter_by(donor_id=current_user.id).all()
    return render_template('my_listings.html', posts=posts)

@main.route('/view_listings')
def view_listings():
    pin_code = None
    user_requests = {}

    if current_user.is_authenticated:
        if current_user.user_type not in REQUESTER_USER_TYPES:
            flash("Only NGOs and Beneficiaries can view listings.", "warning")
            return redirect(url_for("main.login"))

        pin_code = current_user.address[-6:]
        user_requests = {
            r.foodpost_id: r.status
            for r in PickupRequest.query.filter_by(requesting_user_id=current_user.id).all()
        }
    else:
        posts = FoodPost.query.all()
        return render_template('view_listings.html', posts=posts, user_requests=user_requests)

    posts = FoodPost.query.filter_by(pin_code=pin_code).all()

    return render_template('view_listings.html', posts=posts, user_requests=user_requests)

@main.route('/request_pickup/<int:post_id>', methods=['POST'])
@login_required
def request_pickup(post_id):
    
    if current_user.user_type not in ['ngo', 'beneficiary']:
        flash("Only NGOs and Beneficiaries can request pickups.", "warning")
        return redirect(url_for('main.login'))

    
    existing_request = PickupRequest.query.filter_by(foodpost_id=post_id, requesting_user_id=current_user.id).first()
    if existing_request:
        flash("You've already requested this pickup.", "info")
        return redirect(url_for('main.view_listings'))

    
    food_post = FoodPost.query.get(post_id)
    pickup_request = PickupRequest(
        foodpost_id=post_id,
        requesting_user_id=current_user.id,
        status=RequestStatus.PENDING.value
    )
    db.session.add(pickup_request)
    db.session.commit()

    
    send_pickup_request_email_to_donor(
        food_post.donor.email,    
        current_user,
        food_post,
        pickup_request            
    )

    flash("Pickup request submitted! Awaiting donor's response.", "success")
    return redirect(url_for('main.view_listings'))

def send_pickup_request_email_to_donor(donor_email, requesting_user, food_post, pickup_request):
    msg = Message(
        "New Pickup Request for Your Food Post",
        recipients=[donor_email]
    )
    msg.body = f"""
Dear {food_post.donor.name},           

You have a new pickup request for the food item: "{food_post.item_name}" from {requesting_user.name}.
The request is currently in "Pending" status.

Requesting User: {requesting_user.name} ({requesting_user.user_type.capitalize()})
Contact Info: {requesting_user.phone} / {requesting_user.email}

Please review and accept the pickup request by clicking the link below:

Accept Pickup Request: {url_for('main.accept_request', request_id=pickup_request.id, _external=True)}

Thank you for your contribution to reducing food waste!

Best regards,
CorteX Team
"""
    mail.send(msg)


@main.route('/my_requests')
@login_required
def my_requests():
    if current_user.user_type not in ['ngo', 'beneficiary']:
        flash("Only NGOs and Beneficiaries can view their requests.", "warning")
        return redirect(url_for('main.login'))

    requests = PickupRequest.query.filter_by(requesting_user_id=current_user.id).all()
    return render_template('pickup_request.html', requests=requests)


@main.route('/received_requests')
@login_required
def received_requests():
    if current_user.user_type not in ['restaurant', 'donor']:
        flash("Only Restaurants and Donors can view received requests.", "warning")
        return redirect(url_for('main.login'))

    
    food_posts = FoodPost.query.filter_by(donor_id=current_user.id).all()
    requests = PickupRequest.query.filter(PickupRequest.foodpost_id.in_([post.id for post in food_posts])).all()
    return render_template('request_status.html', requests=requests)

@main.route('/accept_request/<int:request_id>', methods=['POST'])
@login_required
def accept_request(request_id):
    if current_user.user_type not in ['restaurant', 'donor']:
        flash("Only Restaurants and Donors can accept requests.", "warning")
        return redirect(url_for('main.login'))

    request = PickupRequest.query.get(request_id)
    if request and request.foodpost.donor_id == current_user.id:
        
        request.status = RequestStatus.ACCEPTED.value
        db.session.commit()

        
        send_acceptance_email(request)

        flash("Pickup request accepted!", "success")
    else:
        flash("Invalid request or you are not the donor.", "danger")

    return redirect(url_for('main.received_requests'))

def send_acceptance_email(request):
    """ Send detailed email to the requesting user about the accepted pickup request. """
    requesting_user = request.requesting_user
    food_post = request.foodpost

    msg = Message(
        "Your Pickup Request has been Accepted",
        recipients=[requesting_user.email]
    )
    msg.body = f"""
Dear {requesting_user.name},

We are pleased to inform you that your pickup request for the food item "{food_post.item_name}" has been accepted by the donor/restaurant.

Here are the details of your request:

- Food Item: {food_post.item_name}
- Donated By: {food_post.donor.name}
- Current Status: Accepted
- Donor's Contact Info: {food_post.donor.phone} / {food_post.donor.email}
- Pickup Location: {food_post.city}, {food_post.pin_code}

Please proceed with the pickup as per the agreed schedule.

Thank you for using CorteX!

Best regards,
CorteX Team
"""
    mail.send(msg)

@main.route('/complete_request/<int:request_id>', methods=['POST'])
@login_required
def complete_request(request_id):
    if current_user.user_type not in ['restaurant', 'donor']:
        flash("Only Restaurants and Donors can complete requests.", "warning")
        return redirect(url_for('main.login'))

    request = PickupRequest.query.get(request_id)
    if request and request.foodpost.donor_id == current_user.id:
        
        request.status = RequestStatus.COMPLETED.value
        db.session.commit()

        
        send_completion_email(request)

        flash("Pickup request completed!", "success")
    else:
        flash("Invalid request or you are not the donor.", "danger")

    return redirect(url_for('main.received_requests'))

def send_completion_email(request):
    """ Send an email to the requesting user about the completed pickup request. """
    requesting_user = request.requesting_user
    food_post = request.foodpost

    
    msg = Message(
        "Your Pickup Request has been Completed",
        recipients=[requesting_user.email]  
    )
    msg.body = f"""
Dear {requesting_user.name},

We are pleased to inform you that your pickup request for the food item "{food_post.item_name}" has been successfully completed by the donor/restaurant.

Here are the details of your request:

- Food Item: {food_post.item_name}
- Donated By: {food_post.donor.name}
- Current Status: Completed
- Donor's Contact Info: {food_post.donor.phone} / {food_post.donor.email} 
- Pickup Location: {food_post.city}, {food_post.pin_code}

Please proceed with the pickup as per the agreed schedule.

Thank you for using CorteX!

Best regards,
CorteX Team
"""
    mail.send(msg)  

@main.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == 'cortex' and password == 'cortex@6708':
            session['admin_logged_in'] = True
            flash('Logged in successfully as Admin.', 'success')
            return redirect(url_for('main.admin_users'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('admin_login.html')

@main.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('main.admin_login'))

from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Admin login required', 'warning')
            return redirect(url_for('main.admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@main.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@main.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.name} deleted successfully.', 'success')
    return redirect(url_for('main.admin_users'))
