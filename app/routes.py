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
import razorpay

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
            login_user(user, remember=True)
            session.permanent = True

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

@main.route('/delivery_dashboard')
@login_required
def delivery_dashboard():
    if current_user.user_type != 'delivery':
        return redirect(url_for('main.home'))

    deliveries = PickupRequest.query.filter_by(delivery_user_id=current_user.id).all()
    # Use the same terminal status used elsewhere ("Completed") so counts stay consistent
    completed = [r for r in deliveries if r.status == "Completed"]
    total_deliveries = len(deliveries)
    total_completed = len(completed)

    daily_counts = defaultdict(int)
    for delivery in deliveries:
        day = delivery.timestamp.strftime('%Y-%m-%d')
        daily_counts[day] += 1

    return render_template(
        'dashboards/delivery_dashboard.html',
        user=current_user,
        total_deliveries=total_deliveries,
        total_completed=total_completed,
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
    user_type = current_user.user_type

    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.email = form.email.data
        current_user.phone = form.phone.data
        current_user.address = form.address.data

        if user_type in ['restaurant', 'donor', 'delivery']:
            current_user.bank_account_holder = form.bank_account_holder.data
            current_user.bank_name = form.bank_name.data
            current_user.account_number = form.account_number.data
            current_user.ifsc_code = form.ifsc_code.data
            current_user.upi_id = form.upi_id.data
            current_user.pan_number = form.pan_number.data

        if form.password.data:
            current_user.set_password(form.password.data)

        try:
            db.session.commit()
            flash("Your profile has been updated successfully!", "success")
            return redirect(url_for('main.profile'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error saving data: {str(e)}", "danger")
    else:
        print(form.errors)  # Debugging errors

    return render_template('edit_profile.html', form=form, user_type=user_type)

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

from opencage.geocoder import OpenCageGeocode
from math import radians, sin, cos, sqrt, atan2

def get_geocoder():
    api_key = current_app.config.get('OPENCAGE_API_KEY')
    return OpenCageGeocode(api_key) if api_key else None

def extract_city(address):
    geocoder = get_geocoder()
    if not geocoder:
        return ""
    try:
        result = geocoder.geocode(address)
        if result and len(result) > 0:
            components = result[0]['components']
            city = components.get('city') or components.get('town') or components.get('village')
            if city:
                return city.lower()
    except Exception as e:
        print(f"City extraction failed: {e}")
    return ""

def get_coordinates(address):
    geocoder = get_geocoder()
    if not geocoder:
        return None, None
    try:
        result = geocoder.geocode(address)
        if result and len(result) > 0:
            lat = result[0]['geometry']['lat']
            lng = result[0]['geometry']['lng']
            return lat, lng
    except Exception as e:
        print(f"Geocoding failed: {e}")
    return None, None

def calculate_distance_km(coord1, coord2):
    if None in coord1 or None in coord2:
        return None
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return round(R * c, 2)

@main.route('/view_listings')
def view_listings():
    user_requests = {}
    filtered_posts = []

    page = request.args.get('page', 1, type=int)
    per_page = 5

    if current_user.is_authenticated:
        if current_user.user_type not in REQUESTER_USER_TYPES:
            flash("Only NGOs and Beneficiaries can view listings.", "warning")
            return redirect(url_for("main.login"))

        user_address = current_user.address.lower()
        user_coords = get_coordinates(current_user.address)

        all_posts = FoodPost.query.all()

        for post in all_posts:
            post_city = post.pin_code.strip().lower()  # This field has city name
            donor_full_address = post.city

            if post_city in user_address:
                post_coords = get_coordinates(donor_full_address)
                distance = calculate_distance_km(user_coords, post_coords)

                filtered_posts.append({
                    'post': post,
                    'distance': distance
                })

        user_requests = {
            r.foodpost_id: r.status
            for r in PickupRequest.query.filter_by(requesting_user_id=current_user.id).all()
        }
    else:
        all_posts = FoodPost.query.all()
        filtered_posts = [{'post': post, 'distance': None} for post in all_posts]

    # Pagination logic for filtered_posts list
    total = len(filtered_posts)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_posts = filtered_posts[start:end]

    # Calculate total pages
    total_pages = (total + per_page - 1) // per_page  # ceil division

    return render_template('view_listings.html',
                           posts=paginated_posts,
                           user_requests=user_requests,
                           page=page,
                           total_pages=total_pages)

@main.route('/request_pickup/<int:post_id>', methods=['POST'])
@login_required
def request_pickup(post_id):
    razorpay_client = current_app.razorpay_client
    if not razorpay_client:
        flash("Payment configuration is missing.", "danger")
        return redirect(url_for('main.view_listings'))

    if current_user.user_type not in ['ngo', 'beneficiary']:
        flash("Only NGOs and Beneficiaries can request pickups.", "warning")
        return redirect(url_for('main.login'))

    food_post = FoodPost.query.get(post_id)
    donor_address = food_post.city or ''
    receiver_address = current_user.address or ''

    donor_coords = get_coordinates(donor_address)
    receiver_coords = get_coordinates(receiver_address)

    if donor_coords and receiver_coords and None not in donor_coords + receiver_coords:
        distance = calculate_distance_km(donor_coords, receiver_coords)
    else:
        distance = 0

    price = float(food_post.price or 0)
    distance = distance or 0

    # Delivery charge
    delivery_charge = 30 if distance <= 5 else 45

    GST_RATE = 0.05

    # Platform fee logic
    platform_fee = 0
    if current_user.user_type == 'ngo':
        if price == 0:
            platform_fee = 10  # fixed ₹10 for free food delivery to NGO
    elif current_user.user_type == 'beneficiary':
        is_first_order = not PickupRequest.query.filter_by(requesting_user_id=current_user.id).first()
        if not is_first_order:
            platform_fee = 10  # platform fee only after first order

    # Commission is charged to donor, so we don't include it here

    # Calculate subtotal (excluding donor commission)
    subtotal = price + platform_fee + delivery_charge

    # GST on the subtotal
    gst = GST_RATE * subtotal

    # Total payable by requester (NGO or beneficiary)
    total_amount = subtotal + gst

    # Existing request logic
    existing_request = PickupRequest.query.filter_by(
        foodpost_id=post_id,
        requesting_user_id=current_user.id
    ).order_by(PickupRequest.id.desc()).first()

    if existing_request:
        if existing_request.status == RequestStatus.COMPLETED.value:
            flash("This pickup has already been completed.", "info")
            return redirect(url_for('main.view_listings'))
        elif existing_request.status == 'Rejected':
            flash("This pickup request was rejected by the donor.", "info")
            return redirect(url_for('main.view_listings'))
        elif existing_request.status == RequestStatus.PENDING.value:
            flash("You’ve already requested this pickup and it’s awaiting donor approval.", "info")
            return redirect(url_for('main.view_listings'))
        elif existing_request.status == 'Payment Pending':
            pickup_request = existing_request
        else:
            pickup_request = PickupRequest(
                foodpost_id=post_id,
                requesting_user_id=current_user.id,
                status='Payment Pending' if total_amount > 0 else RequestStatus.PENDING.value,
                city=current_user.address
            )
            db.session.add(pickup_request)
            db.session.commit()
    else:
        pickup_request = PickupRequest(
            foodpost_id=post_id,
            requesting_user_id=current_user.id,
            status='Payment Pending' if total_amount > 0 else RequestStatus.PENDING.value,
            city=current_user.address
        )
        db.session.add(pickup_request)
        db.session.commit()

    session['pickup_request_id'] = pickup_request.id

    if total_amount > 0:
        razorpay_order = razorpay_client.order.create(dict(
            amount=int(total_amount * 100),  # razorpay expects amount in paise
            currency='INR',
            payment_capture='1',
            notes={
                'user_id': current_user.id,
                'post_id': post_id,
                'pickup_request_id': pickup_request.id
            }
        ))
        session['razorpay_order_id'] = razorpay_order['id']
        session['payment_amount'] = total_amount

        return render_template('payment_page.html',
                        razorpay_order_id=razorpay_order['id'],
                        amount=total_amount,
                        currency='INR',
                        post=food_post,
                        user=current_user,
                        distance=distance,
                        platform_fee=platform_fee,
                        delivery_charge=delivery_charge,
                        gst=gst,
                        phone=current_user.phone)

    else:
        send_pickup_request_email_to_donor(
            food_post.donor.email,
            current_user,
            food_post,
            pickup_request
        )
        flash("Pickup request submitted! Awaiting donor's response.", "success")
        return redirect(url_for('main.view_listings'))

@main.route('/payment_success', methods=['POST'])
@login_required
def payment_success():
    payment_id = request.form.get('razorpay_payment_id')
    order_id = request.form.get('razorpay_order_id')
    signature = request.form.get('razorpay_signature')

    razorpay_client = current_app.razorpay_client
    if not razorpay_client:
        flash("Payment configuration is missing.", "danger")
        return redirect(url_for('main.view_listings'))

    try:
        params_dict = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }
        razorpay_client.utility.verify_payment_signature(params_dict)
    except razorpay.errors.SignatureVerificationError:
        flash("Payment verification failed. Please contact support.", "danger")
        return redirect(url_for('main.view_listings'))

    pickup_request_id = session.get('pickup_request_id')
    if not pickup_request_id:
        flash("Session expired or missing pickup request.", "warning")
        return redirect(url_for('main.view_listings'))

    pickup_request = PickupRequest.query.get(pickup_request_id)
    if not pickup_request:
        flash("Invalid pickup request.", "danger")
        return redirect(url_for('main.view_listings'))

    # Update payment info here
    pickup_request.status = 'Payment Successful'  # change status text
    pickup_request.payment_id = payment_id
    pickup_request.payment_timestamp = datetime.utcnow()
    pickup_request.paid_amount = session.get('payment_amount', 0)
    db.session.commit()

    flash("Payment successful! Your pickup request has been submitted.", "success")
    return redirect(url_for('main.my_requests'))

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

@main.route('/payment_details', methods=['POST'])
@login_required
def payment_details():
    pickup_request_id = request.form.get('pickup_request_id')
    pickup_request = PickupRequest.query.get(pickup_request_id)

    if not pickup_request or pickup_request.requesting_user_id != current_user.id:
        flash("Invalid payment request or unauthorized access.", "danger")
        return redirect(url_for('main.my_requests'))

    return render_template('payment_details.html', payment=pickup_request)

@main.route('/my_requests')
@login_required
def my_requests():
    if current_user.user_type not in ['ngo', 'beneficiary']:
        flash("Only NGOs and Beneficiaries can view their requests.", "warning")
        return redirect(url_for('main.login'))

    pickup_requests = PickupRequest.query.filter_by(requesting_user_id=current_user.id).all()
    completed_payments = PickupRequest.query.filter_by(
        requesting_user_id=current_user.id, status=RequestStatus.COMPLETED.value
    ).all()

    return render_template(
        'pickup_request.html',
        requests=pickup_requests,
        payments=completed_payments
    )

@main.route('/received_requests')
@login_required
def received_requests():
    if current_user.user_type not in ['restaurant', 'donor']:
        flash("Only Restaurants and Donors can view received requests.", "warning")
        return redirect(url_for('main.login'))

    
    food_posts = FoodPost.query.filter_by(donor_id=current_user.id).all()
    requests = PickupRequest.query.filter(PickupRequest.foodpost_id.in_([post.id for post in food_posts])).all()
    delivery_info = {}
    for req in requests:
        if req.delivery_user and req.delivery_user.address:
            donor_coords = get_coordinates(req.foodpost.city)
            requester_coords = get_coordinates(req.requesting_user.address)
            delivery_coords = get_coordinates(req.delivery_user.address)
            delivery_info[req.id] = {
                'partner_name': req.delivery_user.name,
                'partner_phone': req.delivery_user.phone,
                'dist_donor': calculate_distance_km(delivery_coords, donor_coords),
                'dist_requester': calculate_distance_km(delivery_coords, requester_coords)
            }
    return render_template('request_status.html', requests=requests, delivery_info=delivery_info)

@main.route('/find_delivery_partner/<int:request_id>', methods=['POST'])
@login_required
def find_delivery_partner(request_id):
    if current_user.user_type not in ['restaurant', 'donor']:
        flash("Only Restaurants and Donors can find delivery partners.", "warning")
        return redirect(url_for('main.login'))

    pickup_request = PickupRequest.query.get_or_404(request_id)

    if pickup_request.foodpost.donor_id != current_user.id:
        flash("You are not authorized to manage this request.", "danger")
        return redirect(url_for('main.received_requests'))

    if pickup_request.status != RequestStatus.ACCEPTED.value:
        flash("Delivery partner search is only available after accepting the request.", "info")
        return redirect(url_for('main.received_requests'))

    if pickup_request.delivery_user_id:
        flash("A delivery partner is already assigned.", "info")
        return redirect(url_for('main.received_requests'))

    donor_address = pickup_request.foodpost.city
    requester_address = pickup_request.requesting_user.address

    donor_coords = get_coordinates(donor_address)
    requester_coords = get_coordinates(requester_address)

    if None in donor_coords or None in requester_coords:
        flash("Unable to locate addresses. Please verify the donor and requester addresses.", "warning")
        return redirect(url_for('main.received_requests'))

    nearby_candidates = []
    delivery_users = User.query.filter_by(user_type='delivery').all()

    for user in delivery_users:
        if not user.address:
            continue
        delivery_coords = get_coordinates(user.address)
        if None in delivery_coords:
            continue

        dist_to_donor = calculate_distance_km(delivery_coords, donor_coords)
        dist_to_requester = calculate_distance_km(delivery_coords, requester_coords)

        if dist_to_donor is not None and dist_to_requester is not None:
            if dist_to_donor <= 5 and dist_to_requester <= 5:
                nearby_candidates.append((user, dist_to_donor + dist_to_requester))

    if not nearby_candidates:
        flash("No delivery partner found within 5 km of both pickup and drop locations.", "warning")
        return redirect(url_for('main.received_requests'))

    best_candidate = sorted(nearby_candidates, key=lambda x: x[1])[0][0]

    pickup_request.delivery_user_id = best_candidate.id
    pickup_request.status = RequestStatus.DELIVERY_ASSIGNED.value
    pickup_request.delivery_otp = generate_otp()
    pickup_request.requester_otp = generate_otp()
    db.session.commit()

    send_delivery_assignment_email(best_candidate, pickup_request)

    flash(f"Delivery partner assigned: {best_candidate.name} (within 5 km of both locations).", "success")
    return redirect(url_for('main.received_requests'))

@main.route('/accept_request/<int:request_id>', methods=['POST'])
@login_required
def accept_request(request_id):
    if current_user.user_type not in ['restaurant', 'donor']:
        flash("Only Restaurants and Donors can accept requests.", "warning")
        return redirect(url_for('main.login'))

    request = PickupRequest.query.get(request_id)
    if request and request.foodpost.donor_id == current_user.id:
        request.status = RequestStatus.ACCEPTED.value

        food_city = request.foodpost.city.strip().lower() if request.foodpost.city else None

        delivery_candidates = []
        if food_city:
            all_delivery_users = User.query.filter_by(user_type='delivery').all()
            for user in all_delivery_users:
                if user.address and food_city in user.address.lower():
                    delivery_candidates.append(user)

        if delivery_candidates:
            flash(f"Request added to delivery pool for city: {food_city.title()}", "info")
        else:
            flash("No delivery personnel currently available in the matching city.", "warning")

        db.session.commit()

        send_acceptance_email(request)

        flash("Pickup request accepted!", "success")
    else:
        flash("Invalid request or you are not the donor.", "danger")

    return redirect(url_for('main.received_requests'))

@main.route('/reject_request/<int:request_id>', methods=['POST'])
@login_required
def reject_request(request_id):
    if current_user.user_type not in ['restaurant', 'donor']:
        flash("Only Restaurants and Donors can reject requests.", "warning")
        return redirect(url_for('main.login'))

    pickup_request = PickupRequest.query.get(request_id)
    if not pickup_request:
        flash("Invalid pickup request.", "danger")
        return redirect(url_for('main.received_requests'))

    if pickup_request.foodpost.donor_id != current_user.id:
        flash("You are not authorized to reject this request.", "danger")
        return redirect(url_for('main.received_requests'))

    # If no payment was made, reject immediately
    if not pickup_request.payment_id:
        pickup_request.status = RequestStatus.REJECTED.value
        pickup_request.refund_status = "not_refunded"
        db.session.commit()
        flash("Pickup request rejected successfully (no payment to refund).", "info")
        return redirect(url_for('main.received_requests'))

    # Check valid paid_amount
    if pickup_request.paid_amount is None or pickup_request.paid_amount <= 0:
        flash("No valid payment amount found to refund.", "danger")
        return redirect(url_for('main.received_requests'))

    razorpay_client = current_app.razorpay_client
    if not razorpay_client:
        flash("Payment configuration is missing.", "danger")
        return redirect(url_for('main.received_requests'))

    try:
        refund_amount_paise = int(pickup_request.paid_amount * 100)
        current_app.logger.debug(f"Refunding amount (paise): {refund_amount_paise} for payment_id: {pickup_request.payment_id}")

        refund_resp = razorpay_client.payment.refund(pickup_request.payment_id, {
            "amount": refund_amount_paise
        })

        current_app.logger.debug(f"Refund response for payment {pickup_request.payment_id}: {refund_resp}")

        if refund_resp.get('status') == 'processed':
            pickup_request.status = RequestStatus.REJECTED.value
            pickup_request.refund_status = "refunded"
            db.session.commit()
            flash("Pickup request rejected and payment refunded successfully.", "success")
        else:
            db.session.rollback()
            pickup_request.refund_status = "failed"
            db.session.commit()
            flash(f"Refund status is {refund_resp.get('status')}. Request not rejected.", "warning")
            current_app.logger.error(f"Refund status for payment {pickup_request.payment_id}: {refund_resp.get('status')}")
    except razorpay.errors.BadRequestError as e:
        db.session.rollback()
        pickup_request.refund_status = "failed"
        db.session.commit()
        flash("Refund failed due to bad request. Please contact support.", "danger")
        current_app.logger.error(f"BadRequestError during refund: {e}")
    except razorpay.errors.ServerError as e:
        db.session.rollback()
        pickup_request.refund_status = "failed"
        db.session.commit()
        flash("Refund failed due to server error. Please try again later.", "danger")
        current_app.logger.error(f"ServerError during refund: {e}")
    except Exception as e:
        db.session.rollback()
        pickup_request.refund_status = "failed"
        db.session.commit()
        flash(f"An error occurred during refund: {str(e)}", "danger")
        current_app.logger.error(f"Unexpected error during refund: {e}")

    return redirect(url_for('main.received_requests'))

@main.route('/available_deliveries')
@login_required
def available_deliveries():
    if current_user.user_type != 'delivery':
        flash("Only delivery personnel can access this page.", "danger")
        return redirect(url_for('main.home'))

    user_address = current_user.address.lower() if current_user.address else ''

    all_requests = PickupRequest.query.filter_by(
        status=RequestStatus.ACCEPTED.value,
        delivery_user_id=None
    ).order_by(PickupRequest.timestamp.desc()).all()

    filtered_requests = []
    for req in all_requests:
        post = req.foodpost
        donor_city_as_city = post.pin_code.strip().lower()  # city stored in pin_code

        donor_address = post.city or ''  # Use donor full address or city field
        beneficiary_address = req.requesting_user.address.lower() if req.requesting_user.address else ''

        print(f"[DEBUG] Request ID: {req.id}, Donor City (pin_code): {donor_city_as_city}")
        print(f"[DEBUG] Delivery user address: {user_address}")
        print(f"[DEBUG] Donor address: {donor_address}")
        print(f"[DEBUG] Beneficiary address: {beneficiary_address}")

        # Filter: donor city must be part of delivery user's address (to restrict geographically)
        if donor_city_as_city in user_address:
            donor_coords = get_coordinates(donor_address)
            beneficiary_coords = get_coordinates(beneficiary_address)

            print(f"[DEBUG] Donor coords: {donor_coords}")
            print(f"[DEBUG] Beneficiary coords: {beneficiary_coords}")

            if donor_coords is not None and beneficiary_coords is not None:
                if None not in donor_coords and None not in beneficiary_coords:
                    distance = calculate_distance_km(donor_coords, beneficiary_coords)
                else:
                    distance = None
            else:
                distance = None

            filtered_requests.append({
                'request': req,
                'distance': distance
            })

            print(f"[DEBUG] >>> Matched and added with distance = {distance} km")
        else:
            print(f"[DEBUG] Skipped: City '{donor_city_as_city}' not in user address")

    return render_template(
        'available_deliveries.html',
        requests=filtered_requests
    )

@main.route('/my_deliveries')
@login_required
def my_deliveries():
    if current_user.user_type != 'delivery':
        return redirect(url_for('main.home'))

    # Show most recently assigned deliveries first
    deliveries = (
        PickupRequest.query
        .filter_by(delivery_user_id=current_user.id)
        .order_by(PickupRequest.timestamp.desc())  # DESC: recent ones first
        .all()
    )

    return render_template('my_deliveries.html', deliveries=deliveries)

@main.route('/accept_delivery/<int:request_id>', methods=['POST'])
@login_required
def accept_delivery(request_id):
    if current_user.user_type != 'delivery':
        flash("Only delivery personnel can accept deliveries.", "danger")
        return redirect(url_for('main.home'))

    request = PickupRequest.query.get_or_404(request_id)

    # Prevent duplicate acceptance
    if request.delivery_user_id is not None:
        flash("This delivery request has already been accepted.", "warning")
        return redirect(url_for('main.available_deliveries'))

    # Prevent same user from accepting again
    if request.delivery_user_id == current_user.id:
        flash("You have already accepted this delivery.", "info")
        return redirect(url_for('main.my_deliveries'))

    # Assign delivery user and generate OTPs
    request.delivery_user_id = current_user.id
    request.status = "Delivery Assigned"
    request.delivery_otp = generate_otp()
    request.requester_otp = generate_otp()

    db.session.commit()

    flash("You have accepted the delivery task!", "success")
    return redirect(url_for('main.my_deliveries'))

def generate_otp():
    return str(random.randint(100000, 999999))

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

def send_delivery_assignment_email(delivery_user, pickup_request):
    """Notify delivery partner with pickup/drop details and OTPs."""
    requester = pickup_request.requesting_user
    donor = pickup_request.foodpost.donor
    food_post = pickup_request.foodpost

    msg = Message(
        "New Delivery Assigned",
        recipients=[delivery_user.email]
    )
    msg.body = f"""
Hi {delivery_user.name},

You have been assigned a new delivery task.

Request ID: {pickup_request.id}
Food Item: {food_post.item_name}

Pickup From (Donor):
- Name: {donor.name}
- Address: {food_post.city}, {food_post.pin_code}
- Contact: {donor.phone} / {donor.email}

Drop To (Requester):
- Name: {requester.name}
- Address: {requester.address}
- Contact: {requester.phone} / {requester.email}

OTPs:
- Delivery Arrival OTP (share with donor on arrival): {pickup_request.delivery_otp}
- Completion OTP (collect from requester to complete): {pickup_request.requester_otp}

Please complete the pickup and delivery promptly. Thank you!

Best regards,
CorteX Team
"""
    mail.send(msg)

def get_razorpay_client():
    client = current_app.razorpay_client
    if not client:
        raise RuntimeError("Razorpay client not configured")
    return client


def _get_razorpay_resource(client, resource_name):
    """Return a Razorpay resource (contact, fund_account, payout) or raise a clear error."""
    resource = getattr(client, resource_name, None)
    if resource is None:
        raise RuntimeError(
            "Razorpay payouts are unavailable in the current SDK. "
            "Upgrade the razorpay package to a version that supports payouts/contact APIs."
        )
    return resource


def create_contact(user):
    client = get_razorpay_client()
    contact_api = _get_razorpay_resource(client, "contact")

    return contact_api.create({
        "name": user.name,
        "email": user.email,
        "contact": user.phone,
        "type": "employee",
    })


def create_fund_account(user, contact_id):
    client = get_razorpay_client()
    fund_account_api = _get_razorpay_resource(client, "fund_account")

    return fund_account_api.create({
        "contact_id": contact_id,
        "account_type": "bank_account",
        "bank_account": {
            "name": user.bank_account_holder,
            "ifsc": user.ifsc_code,
            "account_number": user.account_number,
        }
    })


def transfer_to_user(user, amount, purpose="payout"):
    client = get_razorpay_client()
    account_number = current_app.config.get('RAZORPAY_ACCOUNT_NUMBER')
    if not account_number:
        raise RuntimeError("Razorpay account number not configured")

    payout_api = _get_razorpay_resource(client, "payout")

    contact = create_contact(user)
    fund_account = create_fund_account(user, contact['id'])

    payout = payout_api.create({
        "account_number": account_number,
        "fund_account_id": fund_account['id'],
        "amount": int(amount * 100),
        "currency": "INR",
        "mode": "IMPS",
        "purpose": purpose,
        "queue_if_low_balance": True,
        "reference_id": f"{user.id}_{purpose}",
        "narration": "Auto Payout from FoodDonation App"
    })
    return payout

@main.route('/complete_delivery/<int:request_id>', methods=['POST'])
@login_required
def complete_delivery(request_id):
    if current_user.user_type != 'delivery':
        flash("Unauthorized access.", "danger")
        return redirect(url_for('main.home'))

    delivery = PickupRequest.query.get_or_404(request_id)
    entered_otp = request.form.get('requester_otp')

    if delivery.delivery_user_id != current_user.id:
        flash("You are not assigned to this delivery.", "danger")
        return redirect(url_for('main.my_deliveries'))

    if delivery.status == 'Completed':
        flash("Delivery already marked as completed.", "info")
        return redirect(url_for('main.my_deliveries'))

    if entered_otp != delivery.requester_otp:
        flash("Invalid OTP. Please try again.", "danger")
        return redirect(url_for('main.my_deliveries'))

    # Step 1: Calculate distance
    donor_coords = get_coordinates(delivery.foodpost.city)
    beneficiary_coords = get_coordinates(delivery.requesting_user.address)
    distance_km = calculate_distance_km(donor_coords, beneficiary_coords)
    print(f"[DEBUG] Delivery Distance: {distance_km} km")

    # Step 2: Calculate delivery charge
    delivery_charge = 45 if distance_km > 5 else 30
    print(f"[DEBUG] Delivery Boy Earns: ₹{delivery_charge}")

    # Step 3: Calculate donor payout
    post_price = float(delivery.foodpost.price or 0)
    commission_rate = 0.20 if post_price < 100 else 0.15
    commission_amount = post_price * commission_rate
    donor_earnings = post_price - commission_amount
    print(f"[DEBUG] Donor Commission: ₹{commission_amount}")
    print(f"[DEBUG] Donor Final Payout: ₹{donor_earnings}")

    try:
        # Step 4: Send money to delivery user
        delivery_payout = transfer_to_user(delivery.delivery_user, delivery_charge, purpose="Delivery Charge")
        print(f"[DEBUG] Delivery Payout Done: {delivery_payout['id']}")

        # Step 5: Send money to donor
        donor_payout = transfer_to_user(delivery.donor, donor_earnings, purpose="Donor Payment")
        print(f"[DEBUG] Donor Payout Done: {donor_payout['id']}")

        # Step 6: Only mark as completed if payments are successful
        delivery.status = 'Completed'
        db.session.commit()

        flash("Delivery marked complete. Payments processed.", "success")
    except RuntimeError as e:
        # Razorpay payouts not available; mark delivery complete but warn about skipped payouts
        db.session.rollback()
        delivery.status = 'Completed'
        db.session.commit()
        flash(f"Delivery marked complete, but payouts were skipped: {str(e)}", "warning")
        print(f"[WARN] Payout skipped: {e}")
    except Exception as e:
        db.session.rollback()  # Roll back any uncommitted DB changes
        flash(f"Payment failed. Delivery not marked complete: {str(e)}", "warning")
        print(f"[ERROR] Payment processing failed: {e}")

    return redirect(url_for('main.my_deliveries'))

@main.route('/verify_arrival/<int:request_id>', methods=['POST'])
@login_required
def verify_arrival(request_id):
    if current_user.user_type not in ['restaurant', 'donor']:
        flash("Only donors can mark arrival.", "warning")
        return redirect(url_for('main.login'))

    pickup_request = PickupRequest.query.get_or_404(request_id)
    entered_otp = request.form.get('otp')  # here flask's request is used

    if not pickup_request or pickup_request.foodpost.donor_id != current_user.id:
        flash("Unauthorized access or request not found.", "danger")
        return redirect(url_for('main.received_requests'))

    if entered_otp == pickup_request.delivery_otp:
        pickup_request.status = RequestStatus.ARRIVED.value
        db.session.commit()
        flash("Delivery personnel arrival confirmed.", "success")
    else:
        flash("Invalid OTP. Please try again.", "danger")

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
