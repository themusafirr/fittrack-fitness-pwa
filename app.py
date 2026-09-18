from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import sqlite3
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash, generate_password_hash
import os
import time
from collections import defaultdict

app = Flask(__name__)

# ===================== 🍪 3 GOLDEN COOKIE FLAGS & SESSION HARDENING =====================
app.config.update(
    SECRET_KEY=os.getenv('FLASK_SECRET_KEY', 'fit_musafir_ultra_hardened_secret_key_2026_!#%&'),
    SESSION_COOKIE_HTTPONLY=True,       # 🛡️ FLAG 1: HttpOnly -> Completely blocks JavaScript/XSS session stealing
    SESSION_COOKIE_SECURE=True,         # 🛡️ FLAG 2: Secure -> Transmitted exclusively over encrypted HTTPS
    SESSION_COOKIE_SAMESITE='Lax',      # 🛡️ FLAG 3: SameSite=Lax -> Blocks CSRF phishing and cross-site hijacking
    PERMANENT_SESSION_LIFETIME=timedelta(days=7)
)
DATABASE = 'fitness.db'

# ===================== 🛡️ BRUTE-FORCE DEFENSE (THC-HYDRA PROTECTION) =====================
failed_attempts = defaultdict(list)

def is_rate_limited(ip, max_attempts=5, window_sec=300):
    now = time.time()
    failed_attempts[ip] = [t for t in failed_attempts[ip] if now - t < window_sec]
    return len(failed_attempts[ip]) >= max_attempts

def record_failed_attempt(ip):
    failed_attempts[ip].append(time.time())

def clear_failed_attempts(ip):
    failed_attempts.pop(ip, None)

# PWA Files
@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js')

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        age INTEGER,
        height REAL,
        weight REAL,
        body_type TEXT,
        goal TEXT,
        target_body TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    conn.commit()
    conn.close()

init_db()

# ===================== PAGES =====================

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        raw_password = request.form['password']
        
        if len(raw_password) < 6:
            flash('Password must be at least 6 characters long!', 'error')
            return render_template('register.html')

        # 🔒 MODERN PASSWORD DEFENSE: High-entropy salt + Scrypt/Werkzeug cryptographic hashing
        hashed_password = generate_password_hash(raw_password)
        
        try:
            conn = get_db()
            c = conn.cursor()
            # 🛡️ SQL INJECTION DEFENSE: Parameterized prepared statements (100% immune to SQLi)
            c.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                     (name, email, hashed_password))
            conn.commit()
            conn.close()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Email already exists or invalid data!', 'error')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    client_ip = request.headers.get('X-Real-IP', request.headers.get('X-Forwarded-For', request.remote_addr))
    
    # 🛑 THC-HYDRA / BRUTE-FORCE RATE LIMITING DEFENSE
    if is_rate_limited(client_ip, max_attempts=5, window_sec=300):
        flash('Too many failed login attempts! Account locked for 5 minutes for security.', 'error')
        return render_template('login.html'), 429

    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        
        conn = get_db()
        c = conn.cursor()
        # 🛡️ SQL INJECTION DEFENSE: Parameterized query
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            clear_failed_attempts(client_ip)
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session.permanent = True
            return redirect(url_for('dashboard'))
        else:
            record_failed_attempt(client_ip)
            flash('Invalid email or password!', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Get user profile
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM user_profiles WHERE user_id = ? ORDER BY created_at DESC LIMIT 1", (user_id,))
    profile = c.fetchone()
    conn.close()
    
    plan = None
    diet = None
    
    if profile and profile['body_type'] and profile['goal']:
        plan, diet = generate_plan(profile)
    
    # Build user object for template
    user_obj = {
        'name': session.get('user_name', 'User'),
        'age': profile.get('age', '') if profile else '',
        'gender': profile.get('gender', 'male') if profile else 'male',
        'height': profile.get('height', '') if profile else '',
        'weight': profile.get('weight', '') if profile else '',
        'body_type': profile.get('body_type', 'average') if profile else 'average',
        'goal': profile.get('goal', 'maintain') if profile else 'maintain'
    }
    
    if request.method == 'POST':
        age = int(request.form['age'])
        height = float(request.form['height'])
        weight = float(request.form['weight'])
        body_type = request.form['body_type']
        goal = request.form['goal']
        target_body = request.form['target_body']
        
        conn = get_db()
        c = conn.cursor()
        c.execute('''INSERT INTO user_profiles 
                     (user_id, age, height, weight, body_type, goal, target_body)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                 (user_id, age, height, weight, body_type, goal, target_body))
        conn.commit()
        conn.close()
        
        return redirect(url_for('dashboard'))
    
    return render_template('dashboard.html', 
                         user=user_obj,
                         profile=profile, 
                         plan=plan, 
                         diet=diet,
                         name=session.get('user_name', 'User'))

# ===================== PLAN GENERATION LOGIC =====================

def generate_plan(profile):
    body_type = profile['body_type']
    goal = profile['goal']
    age = profile['age']
    height = profile['height']
    weight = profile['weight']
    
    # BMI Calculation
    height_m = height / 100
    bmi = weight / (height_m ** 2)
    
    plan = []
    diet = []
    
    # ==================== WORKOUT PLANS ====================
    
    if body_type == 'mota' and goal == 'weight_loss':
        plan = [
            {'day': 'Day 1 - Chest & Cardio', 'exercises': [
                'Bench Press - 3 sets x 12 reps',
                'Dumbbell Flyes - 3 sets x 15 reps',
                'Push-ups - 3 sets x 20 reps',
                'Jumping Jacks - 5 mins',
                'High Knees - 5 mins',
                'Burpees - 3 sets x 10 reps'
            ]},
            {'day': 'Day 2 - Back & Cardio', 'exercises': [
                'Pull-ups - 3 sets x 8 reps',
                'Bent Over Rows - 3 sets x 12 reps',
                'Lat Pulldown - 3 sets x 12 reps',
                'Plank - 3 sets x 60 secs',
                'Mountain Climbers - 5 mins'
            ]},
            {'day': 'Day 3 - Legs & Cardio', 'exercises': [
                'Squats - 4 sets x 15 reps',
                'Lunges - 3 sets x 12 reps each leg',
                'Leg Press - 3 sets x 15 reps',
                'Calf Raises - 4 sets x 20 reps',
                'Jump Squats - 3 sets x 15 reps'
            ]},
            {'day': 'Day 4 - Shoulders & Arms', 'exercises': [
                'Overhead Press - 3 sets x 12 reps',
                'Lateral Raises - 3 sets x 15 reps',
                'Bicep Curls - 3 sets x 12 reps',
                'Tricep Dips - 3 sets x 15 reps',
                'Diamond Push-ups - 3 sets x 12 reps'
            ]},
            {'day': 'Day 5 - Full Body HIIT', 'exercises': [
                'Kettlebell Swings - 4 sets x 20 reps',
                'Battle Ropes - 3 sets x 30 secs',
                'Box Jumps - 3 sets x 12 reps',
                'Rowing Machine - 5 mins',
                'Sprints - 10 x 30 sec sprints'
            ]},
            {'day': 'Day 6 - Active Rest', 'exercises': [
                'Light Walk - 30 mins',
                'Stretching - 20 mins',
                'Yoga - 30 mins'
            ]},
            {'day': 'Day 7 - Rest', 'exercises': ['Complete Rest']}
        ]
        diet = [
            {'meal': 'Breakfast (8:00 AM)', 'items': '2 Egg Whites + 1 Oats Banana Smoothie + 1 Apple'},
            {'meal': 'Mid-Morning (11:00 AM)', 'items': '1 Handful Almonds + Green Tea'},
            {'meal': 'Lunch (1:00 PM)', 'items': '150g Grilled Chicken + 1 Brown Roti + Salad'},
            {'meal': 'Pre-Workout (4:00 PM)', 'items': '1 Banana + Black Coffee'},
            {'meal': 'Post-Workout (6:30 PM)', 'items': '1 Scoop Whey Protein + 1 Glucose'},
            {'meal': 'Dinner (8:30 PM)', 'items': '150g Fish/Tofu + 1 Cup Brown Rice + Vegetables'},
            {'meal': 'Before Bed', 'items': '1 Cup Warm Milk + Turmeric'}
        ]
    
    elif body_type == 'patla' and goal == 'muscle_gain':
        plan = [
            {'day': 'Day 1 - Chest', 'exercises': [
                'Bench Press - 4 sets x 8-10 reps',
                'Incline Dumbbell Press - 4 sets x 10 reps',
                'Cable Flyes - 3 sets x 12 reps',
                'Dips - 3 sets x max reps',
                'Push-ups - 3 sets x 25 reps'
            ]},
            {'day': 'Day 2 - Back', 'exercises': [
                'Deadlifts - 4 sets x 6-8 reps',
                'Pull-ups - 4 sets x 8-10 reps',
                'Barbell Rows - 4 sets x 10 reps',
                'Lat Pulldown - 3 sets x 12 reps',
                'Seated Cable Row - 3 sets x 12 reps'
            ]},
            {'day': 'Day 3 - Shoulders', 'exercises': [
                'Military Press - 4 sets x 8 reps',
                'Dumbbell Shoulder Press - 4 sets x 10 reps',
                'Lateral Raises - 4 sets x 15 reps',
                'Front Raises - 3 sets x 12 reps',
                'Shrugs - 3 sets x 15 reps'
            ]},
            {'day': 'Day 4 - Legs', 'exercises': [
                'Squats - 5 sets x 6-8 reps',
                'Leg Press - 4 sets x 10 reps',
                'Romanian Deadlift - 4 sets x 10 reps',
                'Leg Curls - 3 sets x 12 reps',
                'Calf Raises - 4 sets x 15 reps'
            ]},
            {'day': 'Day 5 - Arms', 'exercises': [
                'Barbell Curls - 4 sets x 10 reps',
                'Hammer Curls - 3 sets x 12 reps',
                'Tricep Pushdown - 4 sets x 12 reps',
                'Skull Crushers - 3 sets x 10 reps',
                'Diamond Push-ups - 3 sets x max'
            ]},
            {'day': 'Day 6 - Rest', 'exercises': ['Light Cardio + Stretching']},
            {'day': 'Day 7 - Rest', 'exercises': ['Complete Rest']}
        ]
        diet = [
            {'meal': 'Breakfast (8:00 AM)', 'items': '4 Whole Eggs + 2 Paratha + 1 Glass Milk'},
            {'meal': 'Mid-Morning (11:00 AM)', 'items': '1 Banana + 10 Cashews + Peanut Butter'},
            {'meal': 'Lunch (1:00 PM)', 'items': '200g Chicken + 2 Roti + Rice + Dal + Salad'},
            {'meal': 'Pre-Workout (4:00 PM)', 'items': '1 Banana + Black Coffee + 1 Glucose'},
            {'meal': 'Post-Workout (6:30 PM)', 'items': '2 Scoop Whey Protein + 1 Scoop Malt'},
            {'meal': 'Dinner (9:00 PM)', 'items': '200g Paneer/Eggs + 2 Roti + Vegetables'},
            {'meal': 'Before Bed', 'items': '1 Glass Milk + 1 Scoop Casein Protein'}
        ]
    
    elif body_type == 'mota' and goal == 'muscle_gain':
        plan = [
            {'day': 'Day 1 - Upper Body (Light)', 'exercises': [
                'Light Bench Press - 3 sets x 12 reps',
                'Light Rows - 3 sets x 12 reps',
                'Light Overhead Press - 3 sets x 12 reps',
                'Light Curls - 3 sets x 15 reps',
                'Light Tricep Work - 3 sets x 15 reps'
            ]},
            {'day': 'Day 2 - Lower Body (Light)', 'exercises': [
                'Bodyweight Squats - 3 sets x 20 reps',
                'Lunges - 3 sets x 10 each leg',
                'Leg Curls - 3 sets x 12 reps',
                'Calf Raises - 3 sets x 15 reps',
                'Plank - 3 sets x 45 secs'
            ]},
            {'day': 'Day 3 - Cardio Focus', 'exercises': [
                'Brisk Walk - 40 mins',
                'Low Intensity Cycling - 20 mins',
                'Swimming - 30 mins',
                'Stretching - 15 mins'
            ]},
            {'day': 'Day 4 - Upper Body', 'exercises': [
                'Dumbbell Press - 3 sets x 12 reps',
                'Lat Pulldown - 3 sets x 12 reps',
                'Shoulder Press - 3 sets x 12 reps',
                'Bicep Curls - 3 sets x 15 reps',
                'Tricep Pushdown - 3 sets x 15 reps'
            ]},
            {'day': 'Day 5 - Lower Body', 'exercises': [
                'Squats - 3 sets x 15 reps',
                'Leg Press - 3 sets x 12 reps',
                'Leg Curls - 3 sets x 12 reps',
                'Calf Raises - 3 sets x 15 reps',
                'Abs - 3 exercises x 15 reps'
            ]},
            {'day': 'Day 6 - Light Cardio', 'exercises': [
                'Brisk Walk - 30 mins',
                'Light Cycling - 20 mins',
                'Stretching - 15 mins'
            ]},
            {'day': 'Day 7 - Rest', 'exercises': ['Complete Rest']}
        ]
        diet = [
            {'meal': 'Breakfast (8:00 AM)', 'items': '3 Egg Whites + Oats + 1 Apple + Black Coffee'},
            {'meal': 'Mid-Morning (11:00 AM)', 'items': '1 Handful Walnuts + Green Tea'},
            {'meal': 'Lunch (1:00 PM)', 'items': '150g Grilled Chicken + Salad + 1 Roti'},
            {'meal': 'Pre-Workout (4:00 PM)', 'items': '1 Orange + Black Coffee'},
            {'meal': 'Post-Workout (6:30 PM)', 'items': '1 Scoop Whey Protein'},
            {'meal': 'Dinner (8:00 PM)', 'items': '150g Fish + Vegetables + 1 Small Bowl Brown Rice'},
            {'meal': 'Before Bed', 'items': '1 Cup Warm Milk + Turmeric'}
        ]
    
    elif body_type == 'patla' and goal == 'weight_loss':
        plan = [
            {'day': 'Day 1 - HIIT + Upper', 'exercises': [
                'Burpees - 4 sets x 10 reps',
                'Push-ups - 4 sets x 15 reps',
                'Mountain Climbers - 4 sets x 30 secs',
                'Dumbbell Press - 3 sets x 12 reps',
                'Plank - 3 sets x 60 secs'
            ]},
            {'day': 'Day 2 - Cardio', 'exercises': [
                'Running - 20 mins',
                'Jump Rope - 15 mins',
                'High Knees - 5 mins',
                'Butt Kicks - 5 mins',
                'Jumping Jacks - 5 mins'
            ]},
            {'day': 'Day 3 - HIIT + Lower', 'exercises': [
                'Jump Squats - 4 sets x 15 reps',
                'Lunges - 3 sets x 12 each',
                'Box Jumps - 3 sets x 12 reps',
                'Squats - 3 sets x 20 reps',
                'Calf Raises - 4 sets x 20 reps'
            ]},
            {'day': 'Day 4 - Strength', 'exercises': [
                'Pull-ups - 4 sets x 8 reps',
                'Rows - 4 sets x 12 reps',
                'Overhead Press - 3 sets x 12 reps',
                'Bicep Curls - 3 sets x 15 reps',
                'Tricep Dips - 3 sets x 15 reps'
            ]},
            {'day': 'Day 5 - Full Body HIIT', 'exercises': [
                'Kettlebell Swings - 4 sets x 20 reps',
                'Battle Ropes - 4 sets x 30 secs',
                'Squat Jumps - 3 sets x 15 reps',
                'Push-up to Renegade Row - 3 sets x 10',
                'Sprints - 10 x 30 sec'
            ]},
            {'day': 'Day 6 - Active Rest', 'exercises': [
                'Yoga - 45 mins',
                'Stretching - 20 mins'
            ]},
            {'day': 'Day 7 - Rest', 'exercises': ['Complete Rest']}
        ]
        diet = [
            {'meal': 'Breakfast (8:00 AM)', 'items': '2 Egg Whites + 1 Oats Pancake + 1 Apple'},
            {'meal': 'Mid-Morning (11:00 AM)', 'items': '1 Handful Almonds + Green Tea'},
            {'meal': 'Lunch (1:00 PM)', 'items': '150g Grilled Chicken + Large Salad + 1 Roti'},
            {'meal': 'Pre-Workout (4:00 PM)', 'items': 'Black Coffee + 1 Banana'},
            {'meal': 'Post-Workout (6:30 PM)', 'items': '1 Scoop Whey Protein + 1 Glucose'},
            {'meal': 'Dinner (8:00 PM)', 'items': '150g Fish + Steamed Vegetables + 1 Small Bowl Quinoa'},
            {'meal': 'Before Bed', 'items': '1 Cup Warm Milk + Turmeric'}
        ]
    
    elif body_type == 'average' and goal == 'muscle_gain':
        plan = [
            {'day': 'Day 1 - Chest & Triceps', 'exercises': [
                'Bench Press - 4 sets x 10 reps',
                'Incline Dumbbell Press - 4 sets x 10 reps',
                'Cable Flyes - 3 sets x 12 reps',
                'Tricep Pushdown - 3 sets x 12 reps',
                'Overhead Tricep Extension - 3 sets x 12 reps'
            ]},
            {'day': 'Day 2 - Back & Biceps', 'exercises': [
                'Deadlifts - 4 sets x 8 reps',
                'Pull-ups - 4 sets x 8-10 reps',
                'Barbell Rows - 4 sets x 10 reps',
                'Bicep Curls - 4 sets x 12 reps',
                'Hammer Curls - 3 sets x 12 reps'
            ]},
            {'day': 'Day 3 - Rest', 'exercises': ['Light Cardio + Stretching']},
            {'day': 'Day 4 - Shoulders & Abs', 'exercises': [
                'Military Press - 4 sets x 10 reps',
                'Lateral Raises - 4 sets x 15 reps',
                'Front Raises - 3 sets x 12 reps',
                'Shrugs - 3 sets x 15 reps',
                'Hanging Leg Raises - 4 sets x 15 reps',
                'Plank - 3 sets x 60 secs'
            ]},
            {'day': 'Day 5 - Legs', 'exercises': [
                'Squats - 5 sets x 8 reps',
                'Leg Press - 4 sets x 10 reps',
                'Romanian Deadlift - 4 sets x 10 reps',
                'Leg Curls - 3 sets x 12 reps',
                'Calf Raises - 4 sets x 15 reps'
            ]},
            {'day': 'Day 6 - Full Body', 'exercises': [
                'Clean and Press - 4 sets x 10 reps',
                'Pull-ups - 3 sets x max',
                'Bench Press - 3 sets x 10 reps',
                'Squats - 3 sets x 12 reps',
                'Battle Ropes - 3 sets x 30 secs'
            ]},
            {'day': 'Day 7 - Rest', 'exercises': ['Complete Rest']}
        ]
        diet = [
            {'meal': 'Breakfast (8:00 AM)', 'items': '4 Whole Eggs + 2 Paratha + 1 Glass Milk'},
            {'meal': 'Mid-Morning (11:00 AM)', 'items': '1 Banana + 10 Almonds + Peanut Butter'},
            {'meal': 'Lunch (1:00 PM)', 'items': '180g Chicken + Rice + Dal + Roti + Salad'},
            {'meal': 'Pre-Workout (4:00 PM)', 'items': '1 Banana + Black Coffee + 1 Glucose'},
            {'meal': 'Post-Workout (6:30 PM)', 'items': '2 Scoop Whey Protein + 1 Malt'},
            {'meal': 'Dinner (9:00 PM)', 'items': '180g Paneer/Eggs + 2 Roti + Vegetables'},
            {'meal': 'Before Bed', 'items': '1 Glass Milk + 1 Scoop Casein'}
        ]
    
    elif body_type == 'average' and goal == 'weight_loss':
        plan = [
            {'day': 'Day 1 - HIIT Upper', 'exercises': [
                'Burpees - 4 sets x 10 reps',
                'Push-ups - 4 sets x 15 reps',
                'Mountain Climbers - 4 sets x 30 secs',
                'Dumbbell Press - 3 sets x 12 reps',
                'Plank - 3 sets x 60 secs'
            ]},
            {'day': 'Day 2 - HIIT Lower', 'exercises': [
                'Jump Squats - 4 sets x 15 reps',
                'Lunges - 3 sets x 12 each',
                'Box Jumps - 3 sets x 12 reps',
                'Calf Raises - 4 sets x 20 reps',
                'High Knees - 5 mins'
            ]},
            {'day': 'Day 3 - Strength', 'exercises': [
                'Pull-ups - 4 sets x 8 reps',
                'Rows - 4 sets x 12 reps',
                'Overhead Press - 3 sets x 12 reps',
                'Squats - 3 sets x 15 reps',
                'Battle Ropes - 3 sets x 30 secs'
            ]},
            {'day': 'Day 4 - Cardio', 'exercises': [
                'Running - 25 mins',
                'Jump Rope - 15 mins',
                'Sprints - 10 x 30 sec',
                'Stretching - 15 mins'
            ]},
            {'day': 'Day 5 - Full Body Circuit', 'exercises': [
                'Kettlebell Swings - 4 sets x 20 reps',
                'Push-ups - 4 sets x 15 reps',
                'Squats - 4 sets x 15 reps',
                'Pull-ups - 3 sets x max',
                'Plank - 3 sets x 60 secs'
            ]},
            {'day': 'Day 6 - Active Rest', 'exercises': [
                'Yoga - 30 mins',
                'Brisk Walk - 20 mins'
            ]},
            {'day': 'Day 7 - Rest', 'exercises': ['Complete Rest']}
        ]
        diet = [
            {'meal': 'Breakfast (8:00 AM)', 'items': '2 Egg Whites + Oats + 1 Apple'},
            {'meal': 'Mid-Morning (11:00 AM)', 'items': 'Handful Almonds + Green Tea'},
            {'meal': 'Lunch (1:00 PM)', 'items': '150g Grilled Chicken + Salad + 1 Roti'},
            {'meal': 'Pre-Workout (4:00 PM)', 'items': 'Black Coffee + 1 Banana'},
            {'meal': 'Post-Workout (6:30 PM)', 'items': '1 Scoop Whey Protein'},
            {'meal': 'Dinner (8:00 PM)', 'items': '150g Fish + Vegetables + Small Bowl Brown Rice'},
            {'meal': 'Before Bed', 'items': '1 Cup Warm Milk'}
        ]
    
    elif body_type == 'patla' and goal == 'maintain':
        plan = [
            {'day': 'Day 1 - Push', 'exercises': [
                'Bench Press - 4 sets x 10 reps',
                'Overhead Press - 4 sets x 10 reps',
                'Lateral Raises - 4 sets x 15 reps',
                'Tricep Pushdown - 3 sets x 12 reps',
                'Push-ups - 3 sets x 20 reps'
            ]},
            {'day': 'Day 2 - Pull', 'exercises': [
                'Deadlifts - 4 sets x 6 reps',
                'Pull-ups - 4 sets x 8 reps',
                'Barbell Rows - 4 sets x 10 reps',
                'Bicep Curls - 3 sets x 12 reps',
                'Face Pulls - 3 sets x 15 reps'
            ]},
            {'day': 'Day 3 - Legs', 'exercises': [
                'Squats - 5 sets x 8 reps',
                'Leg Press - 4 sets x 10 reps',
                'Romanian Deadlift - 4 sets x 10 reps',
                'Leg Curls - 3 sets x 12 reps',
                'Calf Raises - 4 sets x 15 reps'
            ]},
            {'day': 'Day 4 - Rest', 'exercises': ['Light Cardio - 30 mins']},
            {'day': 'Day 5 - Upper', 'exercises': [
                'Incline Press - 4 sets x 10 reps',
                'Lat Pulldown - 4 sets x 12 reps',
                'Shoulder Press - 3 sets x 12 reps',
                'Rows - 3 sets x 12 reps',
                'Arms - 3 sets each exercise'
            ]},
            {'day': 'Day 6 - Lower + Cardio', 'exercises': [
                'Squats - 4 sets x 10 reps',
                'Lunges - 3 sets x 12 each',
                'Calf Raises - 3 sets x 15 reps',
                'Light Cardio - 20 mins'
            ]},
            {'day': 'Day 7 - Rest', 'exercises': ['Complete Rest']}
        ]
        diet = [
            {'meal': 'Breakfast (8:00 AM)', 'items': '3 Eggs + 2 Paratha + Milk'},
            {'meal': 'Mid-Morning (11:00 AM)', 'items': 'Banana + Almonds'},
            {'meal': 'Lunch (1:00 PM)', 'items': '180g Chicken + Rice + Roti + Dal + Salad'},
            {'meal': 'Pre-Workout (4:00 PM)', 'items': 'Banana + Coffee'},
            {'meal': 'Post-Workout (6:30 PM)', 'items': '1 Scoop Whey Protein'},
            {'meal': 'Dinner (9:00 PM)', 'items': '150g Paneer/Eggs + Roti + Vegetables'},
            {'meal': 'Before Bed', 'items': 'Glass Milk'}
        ]
    
    elif body_type == 'mota' and goal == 'maintain':
        plan = [
            {'day': 'Day 1 - Upper Body', 'exercises': [
                'Light Bench Press - 3 sets x 12 reps',
                'Light Rows - 3 sets x 12 reps',
                'Light Overhead Press - 3 sets x 12 reps',
                'Light Curls - 3 sets x 15 reps',
                'Plank - 3 sets x 45 secs'
            ]},
            {'day': 'Day 2 - Lower Body', 'exercises': [
                'Bodyweight Squats - 3 sets x 15 reps',
                'Lunges - 3 sets x 10 each',
                'Leg Curls - 3 sets x 12 reps',
                'Calf Raises - 3 sets x 15 reps',
                'Plank - 3 sets x 45 secs'
            ]},
            {'day': 'Day 3 - Cardio', 'exercises': [
                'Brisk Walk - 40 mins',
                'Light Cycling - 20 mins',
                'Stretching - 15 mins'
            ]},
            {'day': 'Day 4 - Upper Body', 'exercises': [
                'Dumbbell Press - 3 sets x 12 reps',
                'Lat Pulldown - 3 sets x 12 reps',
                'Shoulder Press - 3 sets x 12 reps',
                'Bicep/Tricep Work - 3 sets x 15 reps',
                'Plank - 3 sets x 45 secs'
            ]},
            {'day': 'Day 5 - Lower Body', 'exercises': [
                'Squats - 3 sets x 12 reps',
                'Leg Press - 3 sets x 12 reps',
                'Leg Curls - 3 sets x 12 reps',
                'Calf Raises - 3 sets x 15 reps',
                'Abs - 3 exercises x 15 reps'
            ]},
            {'day': 'Day 6 - Light Cardio', 'exercises': [
                'Brisk Walk - 30 mins',
                'Light Stretching - 15 mins'
            ]},
            {'day': 'Day 7 - Rest', 'exercises': ['Complete Rest']}
        ]
        diet = [
            {'meal': 'Breakfast (8:00 AM)', 'items': '2 Egg Whites + Oats + Apple'},
            {'meal': 'Mid-Morning (11:00 AM)', 'items': 'Handful Almonds + Green Tea'},
            {'meal': 'Lunch (1:00 PM)', 'items': '150g Chicken + Salad + 1 Roti'},
            {'meal': 'Pre-Workout (4:00 PM)', 'items': 'Black Coffee + 1 Banana'},
            {'meal': 'Post-Workout (6:30 PM)', 'items': '1 Scoop Whey Protein'},
            {'meal': 'Dinner (8:00 PM)', 'items': '150g Fish + Vegetables + Small Bowl Brown Rice'},
            {'meal': 'Before Bed', 'items': 'Warm Milk + Turmeric'}
        ]
    
    else:  # average + maintain or any other combo
        plan = [
            {'day': 'Day 1 - Push', 'exercises': [
                'Bench Press - 4 sets x 10 reps',
                'Overhead Press - 4 sets x 10 reps',
                'Lateral Raises - 3 sets x 15 reps',
                'Tricep Pushdown - 3 sets x 12 reps',
                'Push-ups - 3 sets x 15 reps'
            ]},
            {'day': 'Day 2 - Pull', 'exercises': [
                'Deadlifts - 4 sets x 8 reps',
                'Pull-ups - 4 sets x 8 reps',
                'Barbell Rows - 4 sets x 10 reps',
                'Bicep Curls - 3 sets x 12 reps',
                'Face Pulls - 3 sets x 15 reps'
            ]},
            {'day': 'Day 3 - Rest', 'exercises': ['Light Cardio - 30 mins']},
            {'day': 'Day 4 - Legs', 'exercises': [
                'Squats - 5 sets x 8 reps',
                'Leg Press - 4 sets x 10 reps',
                'Romanian Deadlift - 4 sets x 10 reps',
                'Leg Curls - 3 sets x 12 reps',
                'Calf Raises - 4 sets x 15 reps'
            ]},
            {'day': 'Day 5 - Full Body', 'exercises': [
                'Clean and Press - 4 sets x 10 reps',
                'Pull-ups - 3 sets x max',
                'Bench Press - 3 sets x 10 reps',
                'Squats - 3 sets x 12 reps',
                'Plank - 3 sets x 60 secs'
            ]},
            {'day': 'Day 6 - Cardio', 'exercises': [
                'Running/Cycling - 30 mins',
                'Jump Rope - 10 mins',
                'Stretching - 15 mins'
            ]},
            {'day': 'Day 7 - Rest', 'exercises': ['Complete Rest']}
        ]
        diet = [
            {'meal': 'Breakfast (8:00 AM)', 'items': '3 Eggs + 2 Paratha + Milk'},
            {'meal': 'Mid-Morning (11:00 AM)', 'items': 'Banana + Almonds'},
            {'meal': 'Lunch (1:00 PM)', 'items': '180g Chicken + Rice + Roti + Salad'},
            {'meal': 'Pre-Workout (4:00 PM)', 'items': 'Banana + Black Coffee'},
            {'meal': 'Post-Workout (6:30 PM)', 'items': '1 Scoop Whey Protein'},
            {'meal': 'Dinner (9:00 PM)', 'items': '150g Paneer/Eggs + Roti + Vegetables'},
            {'meal': 'Before Bed', 'items': 'Glass Milk'}
        ]
    
    return plan, diet

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
