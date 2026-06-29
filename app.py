from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from mysql.connector import Error
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'change_this_to_random_key_for_security_123'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max

# MySQL Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Chinni@421',  # CHANGE THIS
    'database': 'company'
}

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

def is_logged_in():
    return 'admin_id' in session

def get_total_employees():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM employee')
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count
    except:
        return 0

# ============== PUBLIC PAGES ==============
@app.route("/")
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

# ============== AUTHENTICATION ==============
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        confirm_password = request.form['confirm_password'].strip()
        
        if not username or not password:
            flash('All fields are required.', 'error')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('register'))
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE username=%s', (username,))
            if cursor.fetchone():
                flash('Username already exists.', 'error')
            else:
                hashed_password = generate_password_hash(password)
                cursor.execute(
                    'INSERT INTO users (username, password, role) VALUES (%s, %s, %s)',
                    (username, hashed_password, 'admin')
                )
                conn.commit()
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login'))
            cursor.close()
            conn.close()
        except Error as e:
            flash(f'Database error: {e}', 'error')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                'SELECT * FROM users WHERE username=%s AND role=%s',
                (username, 'admin')
            )
            user = cursor.fetchone()
            
            if user and check_password_hash(user['password'], password):
                session['admin_id'] = user['id']
                session['admin_name'] = user['username']
                session['role'] = user['role']
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password.', 'error')
            
            cursor.close()
            conn.close()
        except Error as e:
            flash(f'Database error: {e}', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

# ============== DASHBOARD ==============
@app.route('/dashboard')
def dashboard():
    if not is_logged_in():
        flash('Please login first!', 'error')
        return redirect(url_for('login'))
    
    employees = []
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM employee ORDER BY eid DESC LIMIT 10')
        employees = cursor.fetchall()
        cursor.close()
        conn.close()
    except Error as e:
        flash(f'Database error: {e}', 'error')
    
    return render_template('dashboard.html', employees=employees, total_employees=get_total_employees())

# ============== ADD EMPLOYEE ==============
@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    if not is_logged_in():
        flash('Please login first!', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        eid = request.form['eid'].strip()
        ename = request.form['ename'].strip()
        edept = request.form['edept'].strip()
        esalary = request.form['esalary'].strip()
        ephone = request.form['ephone'].strip()
        eemail = request.form['eemail'].strip()
        
        if not all([eid, ename, edept, esalary, ephone, eemail]):
            flash('All fields are required.', 'error')
            return redirect(url_for('add_employee'))
        
        employee_photo = None
        if 'employee_photo' in request.files:
            file = request.files['employee_photo']
            if file and file.filename:
                filename = secure_filename(file.filename)
                employee_photo = filename
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT eid FROM employee WHERE eid=%s', (eid,))
            if cursor.fetchone():
                flash('Employee ID already exists!', 'error')
            else:
                cursor.execute(
                    'INSERT INTO employee (eid, ename, edept, esalary, ephone, eemail, employee_photo) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                    (eid, ename, edept, esalary, ephone, eemail, employee_photo)
                )
                conn.commit()
                flash('Employee added successfully!', 'success')
                return redirect(url_for('dashboard'))
            cursor.close()
            conn.close()
        except Error as e:
            flash(f'Database error: {e}', 'error')
    
    return render_template('add_employee.html')

# ============== VIEW EMPLOYEES ==============
@app.route('/view_employees')
def view_employees():
    if not is_logged_in():
        flash('Please login first!', 'error')
        return redirect(url_for('login'))
    
    search_query = request.args.get('search', '').strip()
    employees = []
    
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        if search_query:
            cursor.execute(
                'SELECT * FROM employee WHERE ename LIKE %s OR edept LIKE %s ORDER BY eid DESC',
                (f'%{search_query}%', f'%{search_query}%')
            )
        else:
            cursor.execute('SELECT * FROM employee ORDER BY eid DESC')
        
        employees = cursor.fetchall()
        cursor.close()
        conn.close()
    except Error as e:
        flash(f'Database error: {e}', 'error')
    
    return render_template('view_employees.html', employees=employees, search_query=search_query)

# ============== EMPLOYEE DETAIL ==============
@app.route('/employee/<int:eid>')
def employee_detail(eid):
    if not is_logged_in():
        flash('Please login first!', 'error')
        return redirect(url_for('login'))
    
    employee = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM employee WHERE eid=%s', (eid,))
        employee = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not employee:
            flash('Employee not found!', 'error')
            return redirect(url_for('view_employees'))
    except Error as e:
        flash(f'Database error: {e}', 'error')
        return redirect(url_for('view_employees'))
    
    return render_template('employee_detail.html', employee=employee)

# ============== EDIT EMPLOYEE ==============
@app.route('/edit_employee/<int:eid>', methods=['GET', 'POST'])
def edit_employee(eid):
    if not is_logged_in():
        flash('Please login first!', 'error')
        return redirect(url_for('login'))
    
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'POST':
            ename = request.form['ename'].strip()
            edept = request.form['edept'].strip()
            esalary = request.form['esalary'].strip()
            ephone = request.form['ephone'].strip()
            eemail = request.form['eemail'].strip()
            
            employee_photo = None
            if 'employee_photo' in request.files:
                file = request.files['employee_photo']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    employee_photo = filename
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            if employee_photo:
                cursor.execute(
                    'UPDATE employee SET ename=%s, edept=%s, esalary=%s, ephone=%s, eemail=%s, employee_photo=%s WHERE eid=%s',
                    (ename, edept, esalary, ephone, eemail, employee_photo, eid)
                )
            else:
                cursor.execute(
                    'UPDATE employee SET ename=%s, edept=%s, esalary=%s, ephone=%s, eemail=%s WHERE eid=%s',
                    (ename, edept, esalary, ephone, eemail, eid)
                )
            
            conn.commit()
            flash('Employee updated successfully!', 'success')
            return redirect(url_for('view_employees'))
        
        cursor.execute('SELECT * FROM employee WHERE eid=%s', (eid,))
        employee = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not employee:
            flash('Employee not found!', 'error')
            return redirect(url_for('view_employees'))
    except Error as e:
        flash(f'Database error: {e}', 'error')
        return redirect(url_for('view_employees'))
    
    return render_template('edit_employee.html', employee=employee)

# ============== DELETE EMPLOYEE ==============
@app.route('/delete_employee/<int:eid>')
def delete_employee(eid):
    if not is_logged_in():
        flash('Please login first!', 'error')
        return redirect(url_for('login'))
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT employee_photo FROM employee WHERE eid=%s', (eid,))
        result = cursor.fetchone()
        if result and result[0]:
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], result[0])
            if os.path.exists(photo_path):
                os.remove(photo_path)
        
        cursor.execute('DELETE FROM employee WHERE eid=%s', (eid,))
        conn.commit()
        flash('Employee deleted successfully!', 'success')
        
        cursor.close()
        conn.close()
    except Error as e:
        flash(f'Database error: {e}', 'error')
    
    return redirect(url_for('view_employees'))

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)