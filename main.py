from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from barcode import Code128
from io import BytesIO
from flask_socketio import emit, join_room, leave_room
from flask_login import LoginManager, current_user, login_user, logout_user
from flask_login import UserMixin
from barcode.writer import ImageWriter
from models import db, InventoryItem, Location, User, TransferRequest
from extensions import socketio
import requests
import os

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)),'templates'))
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'

login_manager = LoginManager(app)
socketio.init_app(app)
db.init_app(app)
migrate = Migrate(app, db)

# Define models
#class User(db.Model, UserMixin):
#    __tablename__ = 'user'  # Explicitly define the table name DEBUG
#    __table_args__ = {'extend_existing': True}  # Allow extension of the existing table DEBUG
#    id = db.Column(db.Integer, primary_key=True)
#    username = db.Column(db.String(150), unique=True, nullable=False)
#    password = db.Column(db.String(150), nullable=False)
#    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)

#API keys
MICHELIN_API_KEY = 'mAOgPi9axj9BBcTAmIwFBiqwLssHFRzt'
MICHELIN_API_SECRET = 'WtTecjIs8YghtSHG'

class Location(db.Model):
    __tablename__ = 'location'
    __table_args__ = {'extend_existing': True}  # Allow extending the existing table
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    users = db.relationship(User, backref='location', lazy=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

# Define routes and socket events
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', tire_sizes=get_tire_sizes())

@app.route('/register', methods=['GET', 'POST'])
def register():
    locations = Location.query.all()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        location_id = request.form['location']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password, location_id=location_id)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html', locations=locations)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Fetch user from the database by username
        user = User.query.filter_by(username=username).first()
        
        if user:
            print(f"User found: {user.username}")  # Debugging output
            if check_password_hash(user.password, password):
                print("Password matched.")  # Debugging output
                session['user_id'] = user.id
                login_user(user)
                return redirect(url_for('index'))
            else:
                print("Invalid password.")  # Debugging output
                error = 'Invalid credentials. Please try again.'
        else:
            print(f"User not found with username: {username}")  # Debugging output
            error = 'Invalid credentials. Please try again.'

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    logout_user()
    return redirect(url_for('login'))

@app.context_processor
def inject_locations():
    locations = Location.query.all()  # Fetch all locations from the database
    return {'locations': locations}

@app.route('/dashboard')
def dashboard():
    locations = Location.query.all()  # Fetch all locations from the database
    return render_template('dashboard.html', locations=locations)


@app.route('/warehouse_dashboard')
def warehouse_dashboard():
    return render_template('warehouse_dashboard.html')

# Chat functionality with SocketIO events
@app.route('/chat/<int:user_id>')
def chat(user_id):
    selected_user = User.query.get(user_id)
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.timestamp).all()

    return render_template('chat.html', users=User.query.all(), selected_user=selected_user, messages=messages)

@socketio.on('message')
def handle_message(data):
    room = data['room']
    message = data['message']
    emit('receive_message', {'message': message}, room=room)

@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    emit('receive_message', {'message': f'{username} has entered the room.'}, room=room)

@socketio.on('leave')
def on_leave(data):
    username = data['username']
    room = data['room']
    leave_room(room)
    emit('receive_message', {'message': f'{username} has left the room.'}, room=room)

# Inventory routes
@app.route('/inventory/<int:location_id>', methods=['GET'])
def inventory(location_id):
    inventory_items = InventoryItem.query.filter_by(location_id=location_id).all()
    location = Location.query.get_or_404(location_id)
    return render_template('inventory.html', inventory_items=inventory_items, location=location)

@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if request.method == 'POST':
        try:
            # Extracting data from the form
            sku = request.form.get('sku')  # Define sku
            location_id = request.form.get('location_id')
            item_name = request.form.get('item_name')
            tire_size = request.form.get('tire_size')
            speed_rating = request.form.get('speed_rating')
            load_rating = request.form.get('load_rating')
            quantity = request.form.get('quantity')
            brand = request.form.get('brand')
            model = request.form.get('model')

            # Create a new inventory item
            new_item = InventoryItem(
                sku=sku,  # Fix the undefined sku issue
                location_id=location_id,
                item_name=item_name,
                tire_size=tire_size,
                speed_rating=speed_rating,
                load_rating=load_rating,
                quantity=quantity,
                brand=brand,
                model=model
            )

            db.session.add(new_item)
            db.session.commit()

            # Return success response
            return jsonify({'message': 'Item added successfully!'}), 200
        except Exception as e:
            print(e)
            return jsonify({'error': 'Failed to add item'}), 500
    else:
        locations = Location.query.all()
        return render_template('add_item.html', locations=locations)


# Barcode scanning and inventory transfer routes
@app.route('/scan_barcode', methods=['POST'])
def scan_barcode():
    # Extract barcode and location_id from the request (form or JSON data)
    barcode_data = request.json.get('barcode')
    location_id = request.json.get('location_id')  # Dynamically get the location_id from the request
    tire_size = request.json.get('tire_size', 'Placeholder Size')  # Default value if not provided
    brand = request.json.get('brand', 'Placeholder Brand')  # Default value if not provided
    quantity = request.json.get('quantity', 10)  # Default value if not provided
    
    # Ensure that both barcode and location_id are present in the request
    if barcode_data and location_id:
        # Create a new inventory item using the dynamically provided location_id
        new_item = InventoryItem(
            sku=barcode_data,
            tire_size=tire_size,
            brand=brand,
            quantity=quantity,
            location_id=location_id  # Use the dynamic location_id from the request
        )
        
        # Add the new item to the database
        db.session.add(new_item)
        db.session.commit()

        return jsonify({"message": "Item added via barcode scanning!"}), 200
    else:
        return jsonify({"error": "Barcode and location_id are required."}), 400

def get_tire_details(locale, tyre_id):
    """
    Queries Michelin's B2B API to retrieve details for a specified tire by locale and tire ID.
    """
    api_url = f"https://api.michelin.com/b2b-tyre-details/v1/api/tyres/{locale}/{tyre_id}"
    headers = {
        'Accept': 'application/json',
        'apikey': app.config['MICHELIN_API_KEY']
    }

    response = requests.get(api_url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        return {
            "display_name": data.get('displayName'),
            "claim": data.get('claim'),
            "description": data.get('description'),
            "badges": data.get('badges', {}),
            "articles": data.get('articles', [])
        }
    else:
        return {"error": f"Failed to fetch tire details. Status code: {response.status_code}"}

# route for barcode scanning
@app.route('/fetch_tire_details/<locale>/<tyre_id>', methods=['GET'])
@app.route('/fetch_tire_details/<locale>/<tyre_id>', methods=['GET'])
def fetch_tire_details(locale, tyre_id):
    # Build the API URL using the locale and tyre_id
    api_url = f"https://api.michelin.com/b2b-tyre-details/v1/api/tyres/{locale}/{tyre_id}"
    headers = {
        'Accept': 'application/json',
        'apikey': MICHELIN_API_KEY
    }
    # Send the request to Michelin API
    response = requests.get(api_url, headers=headers)
    
    # Log the request URL for debugging
    print("Request URL:", api_url)
    print("API Status:", response.status_code)
    
    # Check if the response is successful
    if response.status_code == 200:
        data = response.json()
        return jsonify({
            "display_name": data.get('displayName', 'Unknown'),
            "claim": data.get('claim', 'Unknown'),
            "description": data.get('description', 'Unknown'),
            "badges": data.get('badges', {}),
            "articles": data.get('articles', [])
        }), 200
    else:
        # Log the error response for further analysis
        print("API Error Response:", response.text)
        return jsonify({"error": "Failed to fetch tire details"}), response.status_code

@app.route('/generate_barcode/<sku>')
def generate_barcode(sku):
    barcode = Code128(sku, writer=ImageWriter())
    output = BytesIO()
    barcode.write(output)
    output.seek(0)
    return output.getvalue(), 200, {
        'Content-Type': 'image/png',
        'Content-Disposition': f'attachment; filename={sku}.png'
    }

# Transfer system for inventory between locations
@app.route('/request_transfer', methods=['GET', 'POST'])
def request_transfer():
    if request.method == 'POST':
        data = request.form  # Handle transfer logic
        return redirect(url_for('success_page'))
    return render_template('request_transfer.html')

@app.route('/transfer_tire', methods=['POST'])
def transfer_tire():
    # Get data from form
    sku = request.form.get('sku')
    new_location = request.form.get('new_location')

    # Check if the tire with the given SKU exists in inventory
    tire = InventoryItem.query.filter_by(sku=sku).first()

    if not tire:
        return "Tire not found", 404

    # Create a new transfer request
    transfer_request = TransferRequest(
        sku=sku,
        size=tire.tire_size,
        brand=tire.brand,
        current_location=tire.item_location.name,
        new_location=new_location,
        status="Pending"
    )

    # Add and commit the transfer request to the database
    db.session.add(transfer_request)
    db.session.commit()

    return redirect(url_for('transfer_requests'))

# Route to display transfer requests (like the page you posted)
@app.route('/transfer_requests')
def transfer_requests():
    transfer_requests = TransferRequest.query.all()
    return render_template('transfer_tire.html', transfer_requests=transfer_requests)

# Generate inventory report
@app.route('/generate_report', methods=['GET'])
def generate_report():
    # Fetch inventory and generate a summary report
    report = generate_inventory_report()  # A function to process and create reports
    return jsonify(report)

# Inventory report# Inventory report
@app.route('/inventory_report', methods=['GET'])
def inventory_report():
    # Query all tires
    tires = InventoryItem.query.all()

    # Query all locations
    locations = Location.query.all()

    # Prepare report for rendering
    report = {
        "total_tires": len(tires),
        "tires": [{
            "manufacturer": tire.brand,
            "model": tire.size,  # Assuming 'size' is used as 'model' here
            "size": tire.size,
            "quantity_on_hand": tire.quantity,
            "sku": tire.sku,
            "location": tire.location
        } for tire in tires]
    }

    # Render the inventory page with the necessary data
    return render_template('inventory_report', report=report, locations=locations)

# Manage locations
@app.route('/manage_locations')
def manage_locations():
    locations = Location.query.all()  # Fetch predefined locations
    return render_template('manage_locations.html', locations=locations)

# Add a location
@app.route('/edit_location/<int:location_id>', methods=['GET', 'POST'])
def edit_location(location_id):
    location = Location.query.get_or_404(location_id)
    
    if request.method == 'POST':
        location.name = request.form['location_name']
        db.session.commit()
        return redirect(url_for('manage_locations'))
    
    return render_template('edit_location.html', location=location)

@app.route('/add_location', methods=['POST'])
def add_location():
    location_name = request.form['location_name']
    new_location = Location(name=location_name)
    db.session.add(new_location)
    db.session.commit()
    return redirect(url_for('manage_locations'))

@app.route('/delete_location/<int:location_id>', methods=['POST'])
def delete_location(location_id):
    location = Location.query.get_or_404(location_id)
    
    # Remove the location from the database
    db.session.delete(location)
    db.session.commit()
    
    return redirect(url_for('manage_locations'))

# Search for tires by size
@app.route('/search_tires', methods=['GET'])
def search_tires():
    size = request.args.get('size')
    filtered_tires = InventoryItem.query.filter_by(size=size).all()
    return jsonify([{
        'sku': tire.sku,
        'size': tire.size,
        'brand': tire.brand,
        'quantity': tire.quantity,
        'location': tire.location
    } for tire in filtered_tires])

def generate_inventory_report():
    tires = InventoryItem.query.all()
    report_data = {
        "total_tires": len(tires),
        "inventory_summary": [{
            "sku": tire.sku,
            "brand": tire.brand,
            "size": tire.size,
            "quantity": tire.quantity,
            "location": tire.location
        } for tire in tires]
    }
    return report_data

# Initialize the database
def init_db():
    with app.app_context():
        db.create_all()
        if not Location.query.first():
            # Seed locations if they don't exist
            locations = ['Smyrna', 'SE Broad', 'Warehouse', 'La Vergne', 'Memorial']
            for loc in locations:
                new_location = Location(name=loc)
                db.session.add(new_location)
            db.session.commit()

# Dynamic dropdown for tire sizes
def get_tire_sizes():
    sizes = {item.size for item in InventoryItem.query.all()}
    return sorted(sizes)

# Main run block
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensure tables are created
        init_db()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
