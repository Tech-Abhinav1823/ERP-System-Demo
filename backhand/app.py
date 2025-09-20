from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import json
import os
from datetime import datetime
import plotly.graph_objs as go
import plotly.utils

BASE_DIR = os.path.dirname(__file__)
TEMPLATES_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'templates'))
STATIC_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'static'))

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
app.secret_key = 'college_erp_secret_key'

DB_FILE = os.path.join(BASE_DIR, 'database.json')

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            data = json.load(f)
    else:
        data = {}
    # Ensure required keys exist to avoid KeyErrors in templates/routes
    data.setdefault('students', [])
    data.setdefault('teachers', [])
    data.setdefault('admin', [])
    data.setdefault('announcements', [])
    data.setdefault('exam_schedule', [])
    data.setdefault('fee_stats', {'total_students': 0, 'paid': 0, 'unpaid': 0})
    data.setdefault('hostel_rooms', {'occupied': 0, 'available': 0})
    # Seed demo users/data if empty so login works out-of-the-box
    if not data['students']:
        data['students'] = [
            {
                'id': 'ST001', 'name': 'Rahul Sharma', 'email': 'rahul@college.edu', 'password': 'student123',
                'course': 'Computer Science', 'year': 2, 'fee_status': 'Unpaid', 'fee_amount': 50000,
                'hostel_room': 'A-101', 'attendance': 18, 'total_classes': 24, 'notifications': []
            }
        ]
        data['fee_stats']['total_students'] = 1
        data['fee_stats']['unpaid'] = 1
    if not data['teachers']:
        data['teachers'] = [
            {'id': 'T001', 'name': 'Amit Verma', 'email': 'amit@college.edu', 'password': 'teacher123'}
        ]
    if not data['admin']:
        data['admin'] = [
            {'id': 'A001', 'name': 'Admin', 'email': 'admin@college.edu', 'password': 'admin123'}
        ]
    if not data['announcements']:
        data['announcements'] = [
            {'id': 1, 'title': 'Welcome', 'content': 'Semester begins next week.', 'date': '2025-09-01', 'type': 'general', 'from': 'admin'}
        ]
    if not data['exam_schedule']:
        data['exam_schedule'] = [
            {'subject': 'Mathematics', 'date': '2025-09-20', 'time': '10:00 AM', 'type': 'Mid-sem'}
        ]
    if data['hostel_rooms'].get('occupied', 0) == 0 and data['hostel_rooms'].get('available', 0) == 0:
        data['hostel_rooms'] = {'occupied': 150, 'available': 50}
    # Persist seeding if we created defaults
    save_db(data)
    return data

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    user_type = request.form['user_type']
    
    db = load_db()
    
    user_list_key = user_type + 's'
    if user_type == 'admin':
        # The db.json uses 'admin' (singular) for the list of admins
        user_list_key = 'admin'

    for user in db.get(user_list_key, []):
        if user['email'] == email and user['password'] == password:
            session['user_id'] = user['id']
            session['user_type'] = user_type
            session['user_name'] = user['name']
            
            if user_type == 'student':
                return redirect('/student')
            elif user_type == 'teacher':
                return redirect('/teacher')
            else:
                return redirect('/admin')
    
    return redirect('/?error=invalid')

@app.route('/student')
def student_dashboard():
    if 'user_id' not in session or session['user_type'] != 'student':
        return redirect('/')
    
    db = load_db()
    student = next((s for s in db['students'] if s['id'] == session['user_id']), None)
    return render_template('student.html', user=student, student=student, announcements=db.get('announcements', []), exams=db.get('exam_schedule', []))

@app.route('/teacher')  
def teacher_dashboard():
    if 'user_id' not in session or session['user_type'] != 'teacher':
        return redirect('/')
    
    db = load_db()
    teacher = next((t for t in db['teachers'] if t['id'] == session['user_id']), None)
    return render_template('teachers.html', user=teacher, students=db['students'], announcements=db.get('announcements', []))

@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or session['user_type'] != 'admin':
        return redirect('/')
    
    db = load_db()
    
    admin_user = next((a for a in db['admin'] if a['id'] == session['user_id']), None)
    # Generate charts
    fee_chart = go.Pie(labels=['Paid', 'Unpaid'], values=[db['fee_stats']['paid'], db['fee_stats']['unpaid']])
    fee_graph = json.dumps([fee_chart], cls=plotly.utils.PlotlyJSONEncoder)
    
    hostel_chart = go.Bar(x=['Occupied', 'Available'], y=[db['hostel_rooms']['occupied'], db['hostel_rooms']['available']])
    hostel_graph = json.dumps([hostel_chart], cls=plotly.utils.PlotlyJSONEncoder)
    
    return render_template('admin.html', user=admin_user, students=db['students'], fee_graph=fee_graph, hostel_graph=hostel_graph, announcements=db.get('announcements', []))

@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    if 'user_id' not in session or session['user_type'] != 'teacher':
        return jsonify({'error': 'Unauthorized'})
    
    student_id = request.form['student_id']
    status = request.form['status']
    
    db = load_db()
    for student in db['students']:
        if student['id'] == student_id:
            if status == 'present':
                student['attendance'] += 1
            student['total_classes'] += 1
            break
    
    save_db(db)
    return jsonify({'success': True})

@app.route('/update_fee', methods=['POST'])
def update_fee():
    if 'user_id' not in session or session['user_type'] != 'admin':
        return jsonify({'error': 'Unauthorized'})
    
    data = request.get_json()
    student_id = data.get('student_id')
    
    db = load_db()
    for student in db['students']:
        if student['id'] == student_id:
            student['fee_status'] = 'Paid'
            db['fee_stats']['paid'] += 1
            db['fee_stats']['unpaid'] -= 1
            break
    
    save_db(db)
    return jsonify({'success': True, 'receipt': f'Receipt-{student_id}-{datetime.now().strftime("%Y%m%d")}'})

@app.route('/add_student', methods=['POST'])
def add_student():
    if 'user_id' not in session or session['user_type'] != 'admin':
        return jsonify({'error': 'Unauthorized'})
    
    db = load_db()
    new_id = f"ST{str(len(db['students']) + 1).zfill(3)}"
    
    new_student = {
        'id': new_id,
        'name': request.form['name'],
        'email': request.form['email'], 
        'password': 'student123',
        'course': request.form['course'],
        'year': int(request.form['year']),
        'fee_status': 'Unpaid',
        'fee_amount': int(request.form['fee_amount']),
        'hostel_room': request.form['hostel_room'],
        'attendance': 0,
        'total_classes': 0,
        'notifications': []
    }
    
    db['students'].append(new_student)
    db['fee_stats']['total_students'] += 1
    db['fee_stats']['unpaid'] += 1
    save_db(db)
    
    return jsonify({'success': True})

@app.route('/add_announcement', methods=['POST'])
def add_announcement():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'})
    
    db = load_db()
    
    announcement = {
        'id': len(db.get('announcements', [])) + 1,
        'title': request.form['title'],
        'content': request.form['content'],
        'date': datetime.now().strftime('%Y-%m-%d'),
        'type': 'general',
        'from': session['user_type']
    }
    
    if 'announcements' not in db:
        db['announcements'] = []
    db['announcements'].append(announcement)
    
    # Add to all students' notifications
    for student in db['students']:
        student['notifications'].append(announcement['title'])
    
    save_db(db)
    return jsonify({'success': True})

@app.route('/chatbot', methods=['POST'])
def chatbot():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'})
    
    query = request.form['query'].lower()
    db = load_db()
    
    if session['user_type'] == 'student':
        student = next((s for s in db['students'] if s['id'] == session['user_id']), None)
        
        if 'fee' in query:
            return jsonify({'response': f'Your fee status is: {student["fee_status"]}'})
        elif 'exam' in query:
            exams = db.get('exam_schedule', [])
            if exams:
                return jsonify({'response': f'Next exam: {exams[0]["subject"]} on {exams[0]["date"]} at {exams[0]["time"]}'})
            else:
                return jsonify({'response': 'No exams scheduled currently'})
        elif 'attendance' in query:
            percentage = round((student['attendance'] / student['total_classes']) * 100, 2) if student['total_classes'] > 0 else 0
            return jsonify({'response': f'You have attended {student["attendance"]} out of {student["total_classes"]} classes ({percentage}%)'})
        elif 'room' in query or 'hostel' in query:
            return jsonify({'response': f'Your hostel room is: {student["hostel_room"]}'})
    
    return jsonify({'response': 'Sorry, I could not understand your query. Try asking about fees, exams, attendance, or hostel room.'})

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)