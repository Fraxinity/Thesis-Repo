from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')
    department = db.Column(db.String(100), nullable=True) 
    reservations = db.relationship('Reservation', backref='requester', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Room(db.Model):
    __tablename__ = 'rooms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=True)   
    usual_activity = db.Column(db.String(200), nullable=True) # New Field
    # We use the ID (e.g., 'pat', 'gym') as the primary key reference in JS, 
    # but let's keep integer ID for SQL and store the 'code' separately.
    code = db.Column(db.String(20), unique=True, nullable=True) 

class Reservation(db.Model):
    __tablename__ = 'reservations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    
    # Event Details
    activity_purpose = db.Column(db.String(150), nullable=False)
    division = db.Column(db.String(100), nullable=True)
    attendees = db.Column(db.Integer, nullable=True)
    participant_type = db.Column(db.String(50), nullable=True)
    participant_details = db.Column(db.String(100), nullable=True) 
    classification = db.Column(db.String(50), nullable=True)

    # NEW FIELDS FROM FRONTEND UPDATE
    person_in_charge = db.Column(db.String(100), nullable=True)
    contact_number = db.Column(db.String(20), nullable=True)
    
    # Files & Stages
    concept_paper_filename = db.Column(db.String(200), nullable=True)
    final_form_filename = db.Column(db.String(200), nullable=True)
    final_form_uploaded = db.Column(db.Boolean, default=False)
    
    # Denial/Archive
    denial_reason = db.Column(db.Text, nullable=True)
    archived_at = db.Column(db.DateTime, nullable=True) # If not null, it's archived

    # Time
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    date_filed = db.Column(db.DateTime, default=datetime.now)
    
    equipment_data = db.Column(db.Text, nullable=True) 
    
    # Status: 'pending', 'concept-approved', 'approved', 'denied'
    status = db.Column(db.String(20), default='pending')

    def get_equipment(self):
        if self.equipment_data:
            return json.loads(self.equipment_data)
        return {}