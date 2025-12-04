import os
import json
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
from models import db, User, Room, Reservation 

app = Flask(__name__)

# CONFIG
app.config['SECRET_KEY'] = 'thesis-secret-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# UPLOAD CONFIG
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# AI CONFIG
GEMINI_API_KEY = "AIzaSyCj8u8zcuA0r42G2UrI1hwJyX0ABSn2ySI"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent"

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Create tables
with app.app_context():
    db.create_all()

# --- ROUTES ---
    
@app.route('/')
def index():
    rooms = Room.query.all()
    print("--------------------------------------------------")
    print(f"DEBUG CHECK: I found {len(rooms)} rooms in the database.")
    for r in rooms:
        print(f" - Room: {r.name} (ID: {r.id})")
    print("--------------------------------------------------")
    
    # Convert Room objects to dictionaries for JSON serialization
    rooms_dict = [{
        'id': room.id,
        'code': room.code,
        'name': room.name,
        'capacity': room.capacity,
        'description': room.description,
        'usual_activity': room.usual_activity
    } for room in rooms]
    
    return render_template('index.html', user=current_user, rooms=rooms_dict)

@app.route('/login', methods=['POST'])
def login():
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

@app.route('/setup')
def setup():
    with app.app_context():
        db.drop_all()
        db.create_all()
        
        users_to_add = [
            {'user': 'admin', 'pass': 'admin123', 'role': 'admin', 'dept': 'Administration'},
            {'user': 'ccs', 'pass': '1234', 'role': 'student', 'dept': 'College of Computer Studies'},
            {'user': 'cas', 'pass': '1234', 'role': 'student', 'dept': 'College of Arts & Sciences'},
            {'user': 'eng', 'pass': '1234', 'role': 'student', 'dept': 'College of Engineering'},
            {'user': 'avi', 'pass': '1234', 'role': 'student', 'dept': 'College of Nursing'},
        ]
        
        for u in users_to_add:
            new_user = User(username=u['user'], role=u['role'], department=u['dept'])
            new_user.set_password(u['pass'])
            db.session.add(new_user)
            print(f" -> Added Account: {u['user']}")
        
        rooms_list = [
            {"code": "pat", "name": "Performing Arts Theatre", "cap": 1500, "act": "Concerts, Graduation Ceremonies, Large Plays", "desc": "A state-of-the-art facility designed for major university events, featuring professional lighting and sound systems."},
            {"code": "mua", "name": "Medical University Auditorium", "cap": 800, "act": "Lectures, Medical Seminars, Academic Symposia", "desc": "A large, tiered auditorium ideal for professional academic and medical conferences."},
            {"code": "quad", "name": "Quadrangle", "cap": 5000, "act": "School Fairs, Food Stalls, Outdoor Exhibitions", "desc": "The central open field, perfect for large-scale outdoor student gatherings and school-wide events."},
            {"code": "apark", "name": "Achievers Park", "cap": 300, "act": "Quiet Study, Small Gatherings, Relaxation", "desc": "A landscaped area with benches and pathways, suitable for outdoor classes and informal meetings."},
            {"code": "chapel", "name": "Campus Chapel", "cap": 200, "act": "Mass, Religious Services, Weddings", "desc": "A solemn and quiet space for spiritual activities and religious events."},
            {"code": "oval", "name": "Oval", "cap": 10000, "act": "Athletic Training, Track and Field Meets, Large Outdoor Concerts", "desc": "The main sports field with a running track, used primarily for large athletic and physical activities."},
            {"code": "gym", "name": "GYM and Sports Center", "cap": 5000, "act": "Basketball/Volleyball Games, Indoor Sports Fest, Exams", "desc": "A versatile indoor sports complex that can be converted for major exams or indoor conventions."},
            {"code": "spool", "name": "Swimming Pool", "cap": 100, "act": "Swimming Competitions, Training, Aquatic Events", "desc": "The university pool area, restricted mostly to sports and academic aquatic activities."},
            {"code": "maud", "name": "Mini Auditorium", "cap": 250, "act": "Student Organization Meetings, Film Viewings, Small Seminars", "desc": "A smaller, more intimate setting suitable for group discussions and presentations."}
        ]
        
        for r in rooms_list:
            new_room = Room(
                code=r['code'],
                name=r['name'], 
                capacity=r['cap'], 
                usual_activity=r['act'], 
                description=r['desc']
            )
            db.session.add(new_room)
            print(f" -> Added Facility: {r['name']}")
        
        db.session.commit()
        return f"""
        <h1>Setup Complete! 🚀</h1>
        <p>Database has been wiped and re-seeded with:</p>
        <ul>
            <li>{len(users_to_add)} Users created</li>
            <li>{len(rooms_list)} Facilities added</li>
        </ul>
        <a href='/'>Go to Dashboard</a>
        """

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user = User.query.filter_by(username=username).first()
    
    if user and user.check_password(password):
        login_user(user)
        return jsonify({'status': 'success', 'role': user.role, 'username': user.username, 'department': user.department})
    else:
        return jsonify({'status': 'error', 'message': 'Invalid username or password'}), 401

# API endpoint to get all reservations
@app.route('/api/reservations', methods=['GET'])
@login_required
def get_reservations():
    reservations = Reservation.query.all()
    reservations_list = [{
        'id': r.id,
        'user_id': r.user_id,
        'room_id': r.room_id,
        'activity_purpose': r.activity_purpose,
        'start_time': r.start_time.isoformat() if r.start_time else None,
        'end_time': r.end_time.isoformat() if r.end_time else None,
        'status': r.status,
        'date_filed': r.date_filed.isoformat() if r.date_filed else None
    } for r in reservations]
    return jsonify(reservations_list)

# API endpoint to create a reservation
@app.route('/api/reservations', methods=['POST'])
@login_required
def create_reservation():
    data = request.get_json()
    new_reservation = Reservation(
        user_id=current_user.id,
        room_id=data.get('room_id'),
        activity_purpose=data.get('activity_purpose'),
        start_time=datetime.fromisoformat(data.get('start_time')),
        end_time=datetime.fromisoformat(data.get('end_time')),
        status='pending'
    )
    db.session.add(new_reservation)
    db.session.commit()
    return jsonify({'status': 'success', 'id': new_reservation.id})

if __name__ == '__main__':
    app.run(debug=True)