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
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# AI CONFIG (Gemini API)
GEMINI_API_KEY = ""
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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==================== WEB ROUTES ====================

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

# ==================== API ROUTES ====================

# Authentication API - FIXED TO INCLUDE user_id
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user = User.query.filter_by(username=username).first()
    
    if user and user.check_password(password):
        login_user(user)
        return jsonify({
            'status': 'success',
            'user_id': user.id,  # ADDED THIS
            'role': user.role, 
            'username': user.username, 
            'department': user.department
        })
    else:
        return jsonify({'status': 'error', 'message': 'Invalid username or password'}), 401

# Get all rooms
@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    rooms = Room.query.all()
    rooms_list = [{
        'id': room.id,
        'code': room.code,
        'name': room.name,
        'capacity': room.capacity,
        'description': room.description,
        'usual_activity': room.usual_activity
    } for room in rooms]
    return jsonify(rooms_list)

# Get all reservations (Admin sees all, users see their own)
@app.route('/api/reservations', methods=['GET'])
@login_required
def get_reservations():
    if current_user.role == 'admin':
        reservations = Reservation.query.all()
    else:
        reservations = Reservation.query.filter_by(user_id=current_user.id).all()
    
    reservations_list = [{
        'id': r.id,
        'user_id': r.user_id,
        'user': r.requester.username if r.requester else 'Unknown',
        'department': r.requester.department if r.requester else 'Unknown',
        'room_id': r.room_id,
        'activity_purpose': r.activity_purpose,
        'division': r.division,
        'attendees': r.attendees,
        'participant_type': r.participant_type,
        'participant_details': r.participant_details,
        'classification': r.classification,
        'person_in_charge': r.person_in_charge,
        'contact_number': r.contact_number,
        'start_time': r.start_time.isoformat() if r.start_time else None,
        'end_time': r.end_time.isoformat() if r.end_time else None,
        'status': r.status,
        'date_filed': r.date_filed.isoformat() if r.date_filed else None,
        'concept_paper_filename': r.concept_paper_filename,
        'final_form_filename': r.final_form_filename,
        'final_form_uploaded': r.final_form_uploaded,
        'denial_reason': r.denial_reason,
        'equipment_data': r.get_equipment(),
        'archived_at': r.archived_at.isoformat() if r.archived_at else None
    } for r in reservations]
    return jsonify(reservations_list)

# Get single reservation
@app.route('/api/reservations/<int:reservation_id>', methods=['GET'])
@login_required
def get_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    
    # Check permission
    if current_user.role != 'admin' and reservation.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify({
        'id': reservation.id,
        'user_id': reservation.user_id,
        'user': reservation.requester.username if reservation.requester else 'Unknown',
        'department': reservation.requester.department if reservation.requester else 'Unknown',
        'room_id': reservation.room_id,
        'activity_purpose': reservation.activity_purpose,
        'division': reservation.division,
        'attendees': reservation.attendees,
        'participant_type': reservation.participant_type,
        'participant_details': reservation.participant_details,
        'classification': reservation.classification,
        'person_in_charge': reservation.person_in_charge,
        'contact_number': reservation.contact_number,
        'start_time': reservation.start_time.isoformat() if reservation.start_time else None,
        'end_time': reservation.end_time.isoformat() if reservation.end_time else None,
        'status': reservation.status,
        'date_filed': reservation.date_filed.isoformat() if reservation.date_filed else None,
        'concept_paper_filename': reservation.concept_paper_filename,
        'final_form_filename': reservation.final_form_filename,
        'final_form_uploaded': reservation.final_form_uploaded,
        'denial_reason': reservation.denial_reason,
        'equipment_data': reservation.get_equipment(),
        'archived_at': reservation.archived_at.isoformat() if reservation.archived_at else None
    })

# Create reservation
@app.route('/api/reservations', methods=['POST'])
@login_required
def create_reservation():
    try:
        data = request.form
        
        # Handle file upload
        concept_paper = request.files.get('concept_paper')
        if not concept_paper or not allowed_file(concept_paper.filename):
            return jsonify({'error': 'Valid PDF file required'}), 400
        
        filename = secure_filename(concept_paper.filename)
        # Add timestamp to filename to prevent conflicts
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        concept_paper.save(filepath)
        
        # Parse datetime
        start_datetime = datetime.fromisoformat(data.get('start_time'))
        end_datetime = datetime.fromisoformat(data.get('end_time'))
        
        # Create reservation
        new_reservation = Reservation(
            user_id=current_user.id,
            room_id=int(data.get('room_id')),
            activity_purpose=data.get('activity_purpose'),
            division=data.get('division'),
            attendees=int(data.get('attendees', 0)),
            participant_type=data.get('participant_type'),
            participant_details=data.get('participant_details'),
            classification=data.get('classification'),
            person_in_charge=data.get('person_in_charge'),
            contact_number=data.get('contact_number'),
            start_time=start_datetime,
            end_time=end_datetime,
            status='pending',
            concept_paper_filename=filename,
            equipment_data=data.get('equipment_data', '{}')
        )
        
        db.session.add(new_reservation)
        db.session.commit()
        
        return jsonify({'status': 'success', 'id': new_reservation.id})
    
    except Exception as e:
        db.session.rollback()
        print(f"Error creating reservation: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Update reservation
@app.route('/api/reservations/<int:reservation_id>', methods=['PUT'])
@login_required
def update_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    
    # Check permission
    if current_user.role != 'admin' and reservation.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        
        # Update fields
        if 'activity_purpose' in data:
            reservation.activity_purpose = data['activity_purpose']
        if 'division' in data:
            reservation.division = data['division']
        if 'attendees' in data:
            reservation.attendees = data['attendees']
        if 'participant_type' in data:
            reservation.participant_type = data['participant_type']
        if 'participant_details' in data:
            reservation.participant_details = data['participant_details']
        if 'classification' in data:
            reservation.classification = data['classification']
        if 'person_in_charge' in data:
            reservation.person_in_charge = data['person_in_charge']
        if 'contact_number' in data:
            reservation.contact_number = data['contact_number']
        if 'start_time' in data:
            reservation.start_time = datetime.fromisoformat(data['start_time'])
        if 'end_time' in data:
            reservation.end_time = datetime.fromisoformat(data['end_time'])
        if 'room_id' in data:
            reservation.room_id = data['room_id']
        if 'equipment_data' in data:
            reservation.equipment_data = data['equipment_data']
        
        db.session.commit()
        return jsonify({'status': 'success'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Admin: Approve concept (Stage 1)
@app.route('/api/reservations/<int:reservation_id>/approve-concept', methods=['POST'])
@login_required
def approve_concept(reservation_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    reservation = Reservation.query.get_or_404(reservation_id)
    reservation.status = 'concept-approved'
    db.session.commit()
    
    return jsonify({'status': 'success'})

# Admin: Final approval (Stage 2)
@app.route('/api/reservations/<int:reservation_id>/approve-final', methods=['POST'])
@login_required
def approve_final(reservation_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    reservation = Reservation.query.get_or_404(reservation_id)
    
    if not reservation.final_form_uploaded:
        return jsonify({'error': 'Final form not uploaded'}), 400
    
    reservation.status = 'approved'
    db.session.commit()
    
    return jsonify({'status': 'success'})

# Admin: Deny reservation
@app.route('/api/reservations/<int:reservation_id>/deny', methods=['POST'])
@login_required
def deny_reservation(reservation_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    reason = data.get('reason', '')
    
    if not reason:
        return jsonify({'error': 'Denial reason required'}), 400
    
    reservation = Reservation.query.get_or_404(reservation_id)
    reservation.status = 'denied'
    reservation.denial_reason = reason
    db.session.commit()
    
    return jsonify({'status': 'success'})

# User: Upload final form (Stage 2)
@app.route('/api/reservations/<int:reservation_id>/upload-final-form', methods=['POST'])
@login_required
def upload_final_form(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    
    # Check permission
    if reservation.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if reservation.status != 'concept-approved':
        return jsonify({'error': 'Concept not yet approved'}), 400
    
    final_form = request.files.get('final_form')
    if not final_form or not allowed_file(final_form.filename):
        return jsonify({'error': 'Valid PDF file required'}), 400
    
    filename = secure_filename(final_form.filename)
    # Add timestamp to filename to prevent conflicts
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_final_{filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    final_form.save(filepath)
    
    reservation.final_form_filename = filename
    reservation.final_form_uploaded = True
    db.session.commit()
    
    return jsonify({'status': 'success'})

# Archive reservation
@app.route('/api/reservations/<int:reservation_id>/archive', methods=['POST'])
@login_required
def archive_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    
    # Check permission
    if current_user.role != 'admin' and reservation.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    reservation.archived_at = datetime.now()
    db.session.commit()
    
    return jsonify({'status': 'success'})

# Delete reservation
@app.route('/api/reservations/<int:reservation_id>', methods=['DELETE'])
@login_required
def delete_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    
    # Check permission
    if current_user.role != 'admin' and reservation.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Delete associated files
    if reservation.concept_paper_filename:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], reservation.concept_paper_filename))
        except:
            pass
    
    if reservation.final_form_filename:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], reservation.final_form_filename))
        except:
            pass
    
    db.session.delete(reservation)
    db.session.commit()
    
    return jsonify({'status': 'success'})

# Gemini AI Proxy
@app.route('/api/gemini', methods=['POST'])
@login_required
def gemini_proxy():
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')
        
        if not prompt:
            return jsonify({'error': 'Prompt required'}), 400
        
        # Get context data
        rooms = Room.query.all()
        approved_reservations = Reservation.query.filter_by(status='approved').all()
        
        context = {
            'facilities': [{
                'id': r.id,
                'code': r.code,
                'name': r.name,
                'capacity': r.capacity,
                'usual_activity': r.usual_activity,
                'description': r.description
            } for r in rooms],
            'approved_schedule': [{
                'id': r.id,
                'room_id': r.room_id,
                'activity': r.activity_purpose,
                'date': r.start_time.date().isoformat() if r.start_time else None,
                'start_time': r.start_time.time().isoformat() if r.start_time else None,
                'end_time': r.end_time.time().isoformat() if r.end_time else None
            } for r in approved_reservations]
        }
        
        system_instruction = """
You are VacanSee, the official Campus Event Space Reservation Assistant.
Answer only questions about campus facilities and the reservation process.
Be helpful, concise, and professional.
"""
        
        user_query = f"""
The current date/time is {datetime.now().isoformat()}.
Here is the current application state:
{json.dumps(context, indent=2)}

The user asks: {prompt}
"""
        
        # Call Gemini API
        response = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json={
                'contents': [{'parts': [{'text': user_query}]}],
                'systemInstruction': {'parts': [{'text': system_instruction}]}
            },
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.ok:
            result = response.json()
            ai_response = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'No response')
            return jsonify({'response': ai_response})
        else:
            return jsonify({'error': 'AI service error', 'details': response.text}), 500
    
    except Exception as e:
        print(f"Gemini API error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)