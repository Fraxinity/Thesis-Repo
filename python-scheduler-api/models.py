from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

db = SQLAlchemy()

# 1. User Table (Matches Sidebar & Login)
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    # HTML Sidebar shows: "Welcome, [Username] ([Department])"
    role = db.Column(db.String(20), nullable=False, default='student') # 'admin' or 'student'
    department = db.Column(db.String(100), nullable=True) # e.g. "College of Computer Studies"
    
    reservations = db.relationship('Reservation', backref='requester', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 2. Room Table (Matches "Facility / Venue" Dropdown)
class Room(db.Model):
    __tablename__ = 'rooms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False) # e.g. "Performing Arts Theatre"
    capacity = db.Column(db.Integer, nullable=False)
    
    # For the AI Chatbot to read later
    description = db.Column(db.Text, nullable=True)   
    category = db.Column(db.String(50), nullable=True) 

# 3. Reservation Table (Matches "Request Form" & "Print Modal")
class Reservation(db.Model):
    __tablename__ = 'reservations'

    id = db.Column(db.Integer, primary_key=True)
    
    # Relationships
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    
    # --- 1. Event Details (From HTML Fieldset 1) ---
    activity_purpose = db.Column(db.String(150), nullable=False) # HTML ID: event-name
    division = db.Column(db.String(100), nullable=True)          # HTML ID: division
    attendees = db.Column(db.Integer, nullable=True)             # HTML ID: attendees
    
    # HTML Radio: "Student", "Employee", "Others"
    participant_type = db.Column(db.String(50), nullable=True)   
    # HTML Input: "Please specify..." (For when "Others" is selected)
    participant_details = db.Column(db.String(100), nullable=True) 
    
    classification = db.Column(db.String(50), nullable=True)     # HTML ID: classification

    # --- 2. Time Request (From HTML Fieldset 2) ---
    # We store these as DateTime objects to make the Calendar and AI logic easier
    start_time = db.Column(db.DateTime, nullable=False) 
    end_time = db.Column(db.DateTime, nullable=False)
    
    # --- 3. Equipment (From HTML Fieldset 3) ---
    # Stores the JSON string: '{"tables": 5, "projector": true}'
    equipment_data = db.Column(db.Text, nullable=True) 

    # --- System Fields ---
    status = db.Column(db.String(20), default='pending_proof') # 'pending_proof', 'review', 'approved', 'rejected'
    proof_image_path = db.Column(db.String(200), nullable=True)
    date_filed = db.Column(db.DateTime, default=datetime.now) # HTML Print Modal: "Date Filed"
    
    # Google Calendar ID (For Phase 3)
    google_event_id = db.Column(db.String(100), nullable=True)

    # Helper to get equipment back as a list/dict
    def get_equipment(self):
        if self.equipment_data:
            return json.loads(self.equipment_data)
        return {}