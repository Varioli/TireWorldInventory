from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from barcode import Code128
from io import BytesIO
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import LoginManager, current_user, login_user, logout_user
from flask_login import UserMixin
from barcode.writer import ImageWriter

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
db = SQLAlchemy(app)
socketio = SocketIO(app)
login_manager = LoginManager(app)

# Define models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)

class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    users = db.relationship('User', backref='location', lazy=True)

class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(100), nullable=False)
    size = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    location = db.relationship('Location', backref='inventory_items')

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
    return render_template('index', tire_sizes=get_tire_sizes())

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
    return render_template('register', locations=locations)

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

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard')

@app.route('/warehouse_dashboard')
def warehouse_dashboard():
    return render_template('warehouse_dashboard')

# Chat functionality with SocketIO events
@app.route('/chat/<int:user_id>')
def chat(user_id):
    selected_user = User.query.get(user_id)
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.timestamp).all()

    return render_template('chat', users=User.query.all(), selected_user=selected_user, messages=messages)

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
@app.route('/inventory/<location_id>', methods=['GET'])
def inventory(location_id):
    # Fetch inventory for the selected location
    inventory_items = Inventory.query.filter_by(location=location_id).all()
    
    # Prepare the inventory data for the response
    inventory_data = [{
        'sku': item.sku,
        'size': item.size,
        'brand': item.brand,
        'quantity': item.quantity,
        'location': item.location
    } for item in inventory_items]
    
    # Return the data as JSON
    return jsonify(inventory_data)


@app.route('/add_item', methods=['POST', 'GET'])
def add_item():
    if request.method == 'POST':
        data = request.form
        new_tire = Inventory(
            sku=data['sku'],
            size=data['size'],
            brand=data['brand'],
            quantity=int(data['quantity']),
            location=data['location']
        )
        db.session.add(new_tire)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_item.html')

# Barcode scanning and inventory transfer routes
@app.route('/scan_barcode', methods=['POST'])
def scan_barcode():
    barcode_data = request.json.get('barcode')
    if barcode_data:
        new_item = Inventory(
            sku=barcode_data,
            size='Placeholder Size',
            brand='Placeholder Brand',
            quantity=10,
            location='Warehouse'
        )
        db.session.add(new_item)
        db.session.commit()
        return jsonify({"message": "Item added via barcode scanning!"})
    return jsonify({"error": "No barcode data found."}), 400

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
    return render_template('request_transfer')

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
    tires = Inventory.query.all()

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
    return render_template('inventory', report=report, locations=locations)

# Manage locations
@app.route('/manage_locations')
def manage_locations():
    locations = Location.query.all()  # Fetch predefined locations
    return render_template('manage_locations', locations=locations)

# Add a location
@app.route('/add_location', methods=['POST'])
def add_location():
    location_name = request.form.get('location_name')
    # Add logic for adding location to database
    return redirect(url_for('manage_locations'))

# Search for tires by size
@app.route('/search_tires', methods=['GET'])
def search_tires():
    size = request.args.get('size')
    filtered_tires = Inventory.query.filter_by(size=size).all()
    return jsonify([{
        'sku': tire.sku,
        'size': tire.size,
        'brand': tire.brand,
        'quantity': tire.quantity,
        'location': tire.location
    } for tire in filtered_tires])

def generate_inventory_report():
    tires = Inventory.query.all()
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
    db.create_all()
    if not Location.query.first():  # If no locations exist, add the predefined ones
        locations = ['La Vergne', 'Smyrna', 'SW Broad', 'Memorial', 'Commercial', 'TRU']
        for location in locations:
            db.session.add(Location(name=location))
        db.session.commit()

# Dynamic dropdown for tire sizes
def get_tire_sizes():
    sizes = {item.size for item in Inventory.query.all()}
    return sorted(sizes)

# Main run block
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensure tables are created
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
