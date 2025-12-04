import os
import json
import requests # Need this for Gemini API
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime
from models import db, User, Room, Reservation 

app = Flask(__name__)

# CONFIG
app.config['SECRET_KEY'] = 'thesis-secret-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# UPLOAD CONFIG (New!)
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Auto-create folder

# AI CONFIG (New!)
GEMINI_API_KEY = "AIzaSyCj8u8zcuA0r42G2UrI1hwJyX0ABSn2ySI" # Move the key from HTML to here!
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent"

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirect here if user isn't logged in

# NEW (Modern SQLAlchemy)
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def get_frontend_data():
    """
    Fetches all data from SQL and converts it to the exact JSON structure 
    the Frontend JavaScript expects.
    """
    
    # 1. ROOMS
    rooms = Room.query.all()
    rooms_data = []
    for r in rooms:
        rooms_data.append({
            "id": r.id, # Note: Ensure your HTML uses ID or Code consistently. 
            "name": r.name,
            "capacity": r.capacity,
            "usualActivity": r.usual_activity,
            "description": r.description
        })

    # 2. ALL RESERVATIONS (Active & Archived)
    all_res = Reservation.query.all()
    reservations_data = [] # For pending/denied/concept-approved
    schedule_data = []     # For fully approved events
    archive_data = []      # For archived items

    for r in all_res:
        # Convert equipment string back to dict
        eq = r.get_equipment()
        
        # Build the object
        res_obj = {
            "id": r.id,
            "spaceId": r.room_id,
            "activityPurpose": r.activity_purpose,
            "startDate": r.start_time.strftime('%Y-%m-%d'),
            "endDate": r.end_time.strftime('%Y-%m-%d'),
            "startTime": r.start_time.strftime('%H:%M'),
            "endTime": r.end_time.strftime('%H:%M'),
            "user": r.requester.username,
            "department": r.requester.department,
            "status": r.status,
            "division": r.division,
            "attendees": r.attendees,
            "participantType": r.participant_type,
            "participantOther": r.participant_details,
            "classification": r.classification,
            "personInCharge": r.person_in_charge,
            "contactNumber": r.contact_number,
            "dateFiled": r.date_filed.strftime('%Y-%m-%d'),
            "equipment": eq,
            "conceptPaperFilename": r.concept_paper_filename,
            "finalFormFilename": r.final_form_filename,
            "finalFormUploaded": r.final_form_uploaded,
            "denialReason": r.denial_reason,
            "archivedAt": r.archived_at.strftime('%Y-%m-%d') if r.archived_at else None
        }

        # SORTING HAT: Where does this reservation go?
        if r.archived_at:
            res_obj['status'] = 'archived' # Override status for frontend logic
            archive_data.append(res_obj)
        elif r.status == 'approved':
            res_obj['eventName'] = r.activity_purpose
            schedule_data.append(res_obj)
        else:
            # Pending, Concept-Approved, Denied go here
            reservations_data.append(res_obj)

    return rooms_data, reservations_data, schedule_data, archive_data

# --- ROUTES ---
    
# 1. MAIN PAGE LOAD (Injects Data)
@app.route('/')
def index():
    if not current_user.is_authenticated:
        return render_template('index.html', user=None)
    
    # Get the formatted data
    rooms_js, reservations_js, schedule_js, archive_js = get_frontend_data()
    
    return render_template('index.html', 
                           user=current_user,
                           rooms_js=json.dumps(rooms_js),
                           reservations_js=json.dumps(reservations_js),
                           schedule_js=json.dumps(schedule_js),
                           archive_js=json.dumps(archive_js))

# 2. LOGIN/LOGOUT ROUTES
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

# 3. FILE UPLOAD ROUTE
@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and file.filename.endswith('.pdf'):
        filename = secure_filename(file.filename)
        # Add timestamp to make filename unique
        save_name = f"{int(datetime.now().timestamp())}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], save_name))
        return jsonify({'success': True, 'filename': save_name})
    
    return jsonify({'error': 'Invalid file type'}), 400

# 4. AI CHAT ROUTE (Secure Proxy)
@app.route('/api/chat', methods=['POST'])
@login_required
def chat_proxy():
    data = request.get_json()
    
    # Call Google's API from Python so the Key isn't exposed in HTML
    response = requests.post(
        f"{GEMINI_URL}?key={GEMINI_API_KEY}",
        headers={'Content-Type': 'application/json'},
        json=data
    )
    return jsonify(response.json())


# --- SETUP ROUTE (Run this once to create the Admin) ---
@app.route('/setup')
def setup():
    with app.app_context():
        # 1. Reset the database (Wipes old data so you start fresh)
        db.drop_all()
        db.create_all()

        # 2. Define your Department Accounts
        users_to_add = [
            # --- ADMIN (The Superuser) ---
            {'user': 'admin', 'pass': 'admin123', 'role': 'admin', 'dept': 'Administration'},
            
            # --- STUDENT REPRESENTATIVES (Requesters) ---
            {'user': 'ccs', 'pass': '1234', 'role': 'student', 'dept': 'College of Computer Studies'},
            {'user': 'cas', 'pass': '1234', 'role': 'student', 'dept': 'College of Arts & Sciences'},
            {'user': 'eng',  'pass': '1234', 'role': 'student', 'dept': 'College of Engineering'},
            {'user': 'avi', 'pass': '1234', 'role': 'student', 'dept': 'College of Nursing'},
        ]

        for u in users_to_add:
            new_user = User(username=u['user'], role=u['role'], department=u['dept'])
            new_user.set_password(u['pass'])
            db.session.add(new_user)
            print(f" -> Added Account: {u['user']}")

        # 3. CREATE FACILITIES
        rooms_list = [
            {
                "code": "pat", 
                "name": "Performing Arts Theatre", 
                "cap": 1500, 
                "act": "Concerts, Graduation Ceremonies, Large Plays", 
                "desc": "A state-of-the-art facility designed for major university events, featuring professional lighting and sound systems."
            },
            {
                "code": "mua", 
                "name": "Medical University Auditorium", 
                "cap": 800, 
                "act": "Lectures, Medical Seminars, Academic Symposia", 
                "desc": "A large, tiered auditorium ideal for professional academic and medical conferences."
            },
            {
                "code": "quad", 
                "name": "Quadrangle", 
                "cap": 5000, 
                "act": "School Fairs, Food Stalls, Outdoor Exhibitions", 
                "desc": "The central open field, perfect for large-scale outdoor student gatherings and school-wide events."
            },
            {
                "code": "apark", 
                "name": "Achievers Park", 
                "cap": 300, 
                "act": "Quiet Study, Small Gatherings, Relaxation", 
                "desc": "A landscaped area with benches and pathways, suitable for outdoor classes and informal meetings."
            },
            {
                "code": "chapel", 
                "name": "Campus Chapel", 
                "cap": 200, 
                "act": "Mass, Religious Services, Weddings", 
                "desc": "A solemn and quiet space for spiritual activities and religious events."
            },
            {
                "code": "oval", 
                "name": "Oval", 
                "cap": 10000, 
                "act": "Athletic Training, Track and Field Meets, Large Outdoor Concerts", 
                "desc": "The main sports field with a running track, used primarily for large athletic and physical activities."
            },
            {
                "code": "gym", 
                "name": "GYM and Sports Center", 
                "cap": 5000, 
                "act": "Basketball/Volleyball Games, Indoor Sports Fest, Exams", 
                "desc": "A versatile indoor sports complex that can be converted for major exams or indoor conventions."
            },
            {
                "code": "spool", 
                "name": "Swimming Pool", 
                "cap": 100, 
                "act": "Swimming Competitions, Training, Aquatic Events", 
                "desc": "The university pool area, restricted mostly to sports and academic aquatic activities."
            },
            {
                "code": "maud", 
                "name": "Mini Auditorium", 
                "cap": 250, 
                "act": "Student Organization Meetings, Film Viewings, Small Seminars", 
                "desc": "A smaller, more intimate setting suitable for group discussions and presentations."
            }
        ]

        for r in rooms_list:
            new_room = Room(
                code=r['code'], # Note: Ensure your Room model has this column!
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
            <li>{len(users_to_add)} Users created (Admin, Reps, Staff)</li>
            <li>{len(rooms_list)} Facilities added (PAT, Gym, Oval, etc.)</li>
        </ul>
        <a href='/'>Go to Dashboard</a>
        """

# 6. START THE APP
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)