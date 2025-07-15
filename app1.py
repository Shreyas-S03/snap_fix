from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras
import os
from werkzeug.utils import secure_filename
import requests
from google.cloud import vision
import tempfile
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_secret_key')

# Enable Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# PostgreSQL Database Configuration from environment variables
pg_db_config = {
    'host': os.environ.get('PGHOST', 'localhost'),
    'user': os.environ.get('PGUSER', 'postgres'),
    'password': os.environ.get('PGPASSWORD', ''),
    'dbname': os.environ.get('PGDATABASE', 'snap_and_fix'),
    'port': int(os.environ.get('PGPORT', 5432)),
}

# File upload directory
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Database Connection
# Use psycopg2 for PostgreSQL
# Always return a connection with cursor_factory=psycopg2.extras.RealDictCursor for dict-like rows

def get_db_connection():
    return psycopg2.connect(**pg_db_config)


# Flask-Login User Model
class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role


@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    if user_data:
        return User(id=user_data['id'], username=user_data['username'], role=user_data['role'])
    return None


# Routes for User Authentication
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        role = request.form.get('role', 'user')  # Default to 'user' if no role is provided
        
        # Insert the user into the database
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)",
                       (username, email, password, role))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user_data = cursor.fetchone()
        conn.close()

        if user_data and check_password_hash(user_data['password'], password):
            user = User(id=user_data['id'], username=user_data['username'], role=user_data['role'])
            login_user(user)
            return redirect(url_for('user_dashboard' if user_data['role'] == 'user' else 'admin_dashboard'))
        return "Invalid credentials. Please try again.", 401
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# Routes for User Dashboard
@app.route('/dashboard', methods=['GET'])
@login_required
def user_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT *, category, priority FROM reported_issues WHERE user_id = %s", (current_user.id,))
    issues = cursor.fetchall()
    conn.close()
    return render_template('user_dashboard.html', issues=issues, user=current_user)


# Routes for Admin Dashboard
@app.route('/admin', methods=['GET'])
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))  # Redirect non-admin users

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT id, description, location, image_path, status, category, priority FROM reported_issues")
    issues = cursor.fetchall()
    conn.close()
    return render_template('admin_dashboard.html', issues=issues, user=current_user)


# Update Issue Status (Admin Only)
@app.route('/update_status/<int:issue_id>', methods=['POST'])
@login_required
def update_status(issue_id):
    if current_user.role != 'admin':
        return "Unauthorized access.", 403  # Only admins can update statuses

    status = request.form['status']
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("UPDATE reported_issues SET status = %s WHERE id = %s", (status, issue_id))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))  # Redirect back to the admin dashboard


# Report an Issue Page (Displays index.html)
@app.route('/report')
@login_required
def report_issue():
    return render_template('index.html', user=current_user, google_maps_api_key=GOOGLE_MAPS_API_KEY)  # Renders the form for reporting issues


# Google Maps/Vision API Key from environment variable
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_API_KEY', 'AIzaSyDxhFV__dTsV5pO-8C664Ytzuk_0tEiGVI')

def geocode_address(address):
    url = f'https://maps.googleapis.com/maps/api/geocode/json'
    params = {'address': address, 'key': GOOGLE_MAPS_API_KEY}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'OK' and data['results']:
            location = data['results'][0]['geometry']['location']
            return location['lat'], location['lng']
    return None, None


# Report an Issue Submission
@app.route('/upload', methods=['POST'])
@login_required
def upload():
    description = request.form.get("description")
    location = request.form.get("location")
    latitude = request.form.get("latitude")
    longitude = request.form.get("longitude")
    category = request.form.get("category", "other")
    priority = request.form.get("priority", "medium")

    if not description or not location or 'file' not in request.files:
        return jsonify({"error": "All fields are required."}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected."}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join('static', 'uploads', filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    relative_path = f"uploads/{filename}"  # Store relative path

    # Use submitted lat/lng if provided, otherwise geocode
    if latitude and longitude:
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except Exception:
            latitude, longitude = geocode_address(location)
    else:
        latitude, longitude = geocode_address(location)

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(
        "INSERT INTO reported_issues (description, category, priority, location, image_path, status, user_id, latitude, longitude) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (description, category, priority, location, relative_path, 'reported', current_user.id, latitude, longitude)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Issue reported successfully!"})

@app.route('/admin/view_map', methods=['GET'])
@login_required
def view_map():
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))  # Redirect non-admin users

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT id, description, location, image_path, latitude, longitude, category, priority FROM reported_issues WHERE LOWER(status::text) IN ('in-progress', 'reported')")
    issues = cursor.fetchall()
    conn.close()

    # Geocode any issues with missing coordinates
    for issue in issues:
        if issue['latitude'] is None or issue['longitude'] is None:
            lat, lng = geocode_address(issue['location'])
            if lat and lng:
                issue['latitude'] = lat
                issue['longitude'] = lng
                # Update the database with the geocoded coordinates
                conn = get_db_connection()
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute("UPDATE reported_issues SET latitude = %s, longitude = %s WHERE id = %s", (lat, lng, issue['id']))
                conn.commit()
                conn.close()

    # Pass the locations of issues and the API key to the template
    return render_template('view_map.html', issues=issues, google_maps_api_key=GOOGLE_MAPS_API_KEY)


# Home Route (Display login page for unauthenticated users)
@app.route('/')
def home():
    if current_user.is_authenticated:
        # Redirect to user/admin dashboard based on user role
        return redirect(url_for('user_dashboard' if current_user.role == 'user' else 'admin_dashboard'))
    return render_template('login.html')  # Show login page if user is not logged in


def analyze_issue_image(path):
    client = vision.ImageAnnotatorClient()
    with open(path, "rb") as image_file:
        content = image_file.read()
    image = vision.Image(content=content)

    # Label Detection
    label_response = client.label_detection(image=image)
    labels = [(label.description.lower(), label.score) for label in label_response.label_annotations]

    # Object Localization
    object_response = client.object_localization(image=image)
    objects = [(obj.name.lower(), obj.score) for obj in object_response.localized_object_annotations]

    # Debug logging for Vision API results
    print("[Vision API] Labels:", labels)
    print("[Vision API] Objects:", objects)

    # Image Properties
    prop_response = client.image_properties(image=image)
    props = prop_response.image_properties_annotation
    dominant_colors = [
        {
            'fraction': color.pixel_fraction,
            'red': color.color.red,
            'green': color.color.green,
            'blue': color.color.blue
        }
        for color in props.dominant_colors.colors
    ] if props.dominant_colors.colors else []

    # Enhanced: Prefer problem label if both context and problem present
    category_map = {
        'pothole': 'potholes',
        'hole': 'potholes',
        'crack': 'potholes',
        'road damage': 'potholes',
        'damaged road': 'potholes',
        'asphalt': 'potholes',
        'broken road': 'potholes',
        'sinkhole': 'potholes',
        'puddle': 'potholes',
        'streetlight': 'streetlights',
        'garbage': 'garbage',
        'waste': 'garbage',
        'trash': 'garbage',
        'rubbish': 'garbage',
        'traffic signal': 'traffic_signals',
        'signal': 'traffic_signals',
        'road sign': 'road_signs',
        'sidewalk': 'sidewalks',
        'footpath': 'sidewalks',
        'drainage': 'drainage',
        'sewage': 'drainage',
        'road': 'road',
        'bus stop': 'bus_stop',
        'bus stand': 'bus_stop',
        'street': 'road',
    }
    problem_categories = ['garbage', 'potholes', 'drainage', 'traffic_signals', 'streetlights']
    context_categories = ['sidewalks', 'road', 'bus_stop', 'road_signs']
    best_match = 'other'
    best_score = 0
    best_source = ''
    found_categories = set()
    found_scores = {}
    # Collect all found categories and their best scores
    for label, score in labels:
        for key, value in category_map.items():
            if key in label:
                found_categories.add(value)
                if value not in found_scores or score > found_scores[value]:
                    found_scores[value] = score
    for obj_name, obj_score in objects:
        for key, value in category_map.items():
            if key in obj_name:
                found_categories.add(value)
                if value not in found_scores or obj_score > found_scores[value]:
                    found_scores[value] = obj_score
    # Prefer problem category if present
    suggested_category = 'other'
    category_confidence = 0
    for cat in problem_categories:
        if cat in found_categories and found_scores[cat] >= 0.5:
            suggested_category = cat
            category_confidence = found_scores[cat]
            break
    # If no problem category, prefer context category
    if suggested_category == 'other':
        for cat in context_categories:
            if cat in found_categories and found_scores[cat] >= 0.5:
                suggested_category = cat
                category_confidence = found_scores[cat]
                break
    # If still nothing, use highest scoring found category
    if suggested_category == 'other' and found_scores:
        best_cat = max(found_scores, key=lambda k: found_scores[k])
        suggested_category = best_cat
        category_confidence = found_scores[best_cat]
    # If still nothing, fallback
    if suggested_category == 'other':
        category_confidence = 0

    # Enhanced: Priority logic
    suggested_priority = 'medium'
    urgent_keywords = ['danger', 'dangerous', 'emergency', 'accident', 'fire', 'collapse']
    urgent_found = any(any(uk in label for uk in urgent_keywords) for label, _ in labels)
    if category_confidence > 0.9 or urgent_found:
        suggested_priority = 'urgent'
    elif suggested_category == 'potholes':
        suggested_priority = 'high'
    elif suggested_category == 'garbage':
        suggested_priority = 'medium'
    elif suggested_category == 'drainage':
        suggested_priority = 'high'
    elif suggested_category == 'traffic_signals':
        suggested_priority = 'high'
    elif suggested_category == 'streetlights':
        suggested_priority = 'medium'
    elif suggested_category == 'sidewalks':
        suggested_priority = 'low'
    elif suggested_category == 'road_signs':
        suggested_priority = 'medium'
    elif suggested_category == 'road':
        suggested_priority = 'medium'
    elif suggested_category == 'bus_stop':
        suggested_priority = 'medium'
    else:
        suggested_priority = 'medium'

    # Heuristic: Image quality (improved: check brightness and color fraction)
    is_dark = False
    is_low_color = False
    if dominant_colors:
        avg_brightness = sum([0.299*c['red'] + 0.587*c['green'] + 0.114*c['blue'] for c in dominant_colors]) / len(dominant_colors)
        if avg_brightness < 60:
            is_dark = True
        if max([c['fraction'] for c in dominant_colors]) > 0.8:
            is_low_color = True
    if is_dark:
        quality_feedback = 'Image is too dark, please retake with better lighting.'
    elif is_low_color:
        quality_feedback = 'Image may be blurry or overexposed, please check.'
    else:
        quality_feedback = 'Image quality looks good.'

    return {
        'labels': [l for l, _ in labels],
        'objects': objects,
        'dominant_colors': dominant_colors,
        'suggested_category': suggested_category,
        'category_confidence': round(category_confidence, 2),
        'suggested_priority': suggested_priority,
        'quality_feedback': quality_feedback
    }

# New endpoint for analyzing uploaded image (AJAX)
@app.route('/analyze_image', methods=['POST'])
@login_required
def analyze_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded.'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected.'}), 400
    # Save to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp:
        file.save(temp.name)
        temp_path = temp.name
    try:
        result = analyze_issue_image(temp_path)
    except Exception as e:
        return jsonify({'error': f'Vision API error: {str(e)}'}), 500
    finally:
        import os
        os.remove(temp_path)
    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True)
