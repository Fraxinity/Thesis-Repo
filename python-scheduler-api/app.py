from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, Room, Reservation # Importing from the models.py file we made

import json
import os

app = Flask(__name__)

# --- CONFIGURATION ---
# Secret key is needed for session security (keep this secret in real life!)
app.config['SECRET_KEY'] = 'thesis-secret-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirect here if user isn't logged in

# NEW (Modern SQLAlchemy)
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- ROUTES ---
    
@app.route('/')
def index():
    # 1. Fetch rooms
    rooms = Room.query.all()

    # --- THE SNITCH: Print to Terminal ---
    print("--------------------------------------------------")
    print(f"DEBUG CHECK: I found {len(rooms)} rooms in the database.")
    for r in rooms:
        print(f" - Room: {r.name} (ID: {r.id})")
    print("--------------------------------------------------")
    # -------------------------------------

    # Send them to the template
    return render_template('index.html', user=current_user, rooms=rooms)

@app.route('/login', methods=['POST'])
def login():
    # Get data from the form (we will update the HTML to send this)
    username = request.form.get('username')
    password = request.form.get('password')

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        login_user(user)
        return redirect(url_for('index'))
    else:
        flash('Invalid username or password')
        return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# --- SETUP ROUTE (Run this once to create the Admin) ---
@app.route('/setup')
def setup():
    with app.app_context():
        db.create_all()
        
        # 1. Create Users
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin', department='Administration')
            admin.set_password('admin123')
            db.session.add(admin)
            
            user = User(username='CCS', role='student', department='College of Computer Studies')
            user.set_password('user123')
            db.session.add(user)
            

        # 2. Create Rooms (From your HTML Event Spaces)
        if not Room.query.first():
            rooms_list = [
                {"name": "Performing Arts Theatre", "capacity": 500},
                {"name": "Medical University Auditorium", "capacity": 300},
                {"name": "Quadrangle", "capacity": 1000},
                {"name": "Achievers Park", "capacity": 200},
                {"name": "Campus Chapel", "capacity": 100},
                {"name": "Oval", "capacity": 2000},
                {"name": "GYM and Sports Center", "capacity": 800},
                {"name": "Swimming Pool", "capacity": 50},
                {"name": "Mini Auditorium", "capacity": 150}
            ]
            for r in rooms_list:
                new_room = Room(name=r['name'], capacity=r['capacity'])
                db.session.add(new_room)

        db.session.commit()
        return "Database Setup Complete! Users and Rooms match your HTML."
    
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() # Get the JS data
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        login_user(user) # This sets the "Logged In" cookie
        return jsonify({'status': 'success', 'role': user.role})
    else:
        return jsonify({'status': 'error', 'message': 'Invalid username or password'}), 401
    

if __name__ == '__main__':
    app.run(debug=True)