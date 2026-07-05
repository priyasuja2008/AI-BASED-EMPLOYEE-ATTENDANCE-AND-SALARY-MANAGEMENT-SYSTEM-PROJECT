import face_recognition
import numpy as np
import cv2
import base64
import mysql.connector
import os
from datetime import datetime,timedelta

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    make_response,
    jsonify,
    Response
)

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer
)

app = Flask(__name__)
app.secret_key = "attendance_secret_key"

known_encodings = []
known_names = []
latest_frame=None

def load_faces():

    global known_encodings
    global known_names

    known_encodings = []
    known_names = []

    face_folder = "static/uploads/faces"

    if os.path.exists(face_folder):

        for file in os.listdir(face_folder):

            if file.endswith((".jpg", ".jpeg", ".png")):

                image = face_recognition.load_image_file(
                    os.path.join(face_folder, file)
                )

                encodings = face_recognition.face_encodings(image)

                if len(encodings) > 0:

                    known_encodings.append(encodings[0])

                    known_names.append(
                        os.path.splitext(file)[0]
                    )

camera_message=""
last_person=""
last_time=datetime.min
recognised_employee=""

# ---------------- Camera ---------------- #

video_camera = cv2.VideoCapture(0)

if not video_camera.isOpened():
    print("❌ Unable to Open Camera")

# ---------------- Load Saved Faces ---------------- #

load_faces()

# ---------------- DATABASE CONNECTION ---------------- #

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Priya123@",      # Your MySQL password
        database="attendance_system"
    )

# ---------------- HOME ---------------- #

@app.route('/')
def home():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE role='admin'")
    admin = cursor.fetchone()

    cursor.close()
    conn.close()

    if admin:
        return redirect(url_for('login'))
    else:
        return redirect(url_for('signup'))

# ---------------- SIGNUP ---------------- #

@app.route('/signup', methods=['GET', 'POST'])
def signup():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Allow only one admin account
    cursor.execute("SELECT * FROM users WHERE role='admin'")
    admin = cursor.fetchone()

    if admin:
        cursor.close()
        conn.close()
        flash("Admin account already exists. Please login.")
        return redirect(url_for('login'))

    if request.method == 'POST':

        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash("Passwords do not match.")
            cursor.close()
            conn.close()
            return redirect(url_for('signup'))

        cursor.execute(
            "SELECT * FROM users WHERE username=%s",
            (username,)
        )

        existing_user = cursor.fetchone()

        if existing_user:
            flash("Username already exists.")
            cursor.close()
            conn.close()
            return redirect(url_for('signup'))

        cursor.execute("""
            INSERT INTO users(username,email,password,role)
            VALUES(%s,%s,%s,%s)
        """, (username, email, password, "admin"))

        conn.commit()

        cursor.close()
        conn.close()

        flash("Account created successfully.")
        return redirect(url_for('login'))

    cursor.close()
    conn.close()

    return render_template("signup.html")

# ---------------- LOGIN ---------------- #

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (username, password)
        )

        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:
            session['user'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))

        flash("Invalid Username or Password")

    return render_template("login.html")

# ---------------- DASHBOARD ---------------- #

@app.route('/dashboard')
def dashboard():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Total Employees
    cursor.execute("SELECT COUNT(*) AS total FROM employees")
    total_employees = cursor.fetchone()['total']

    # Present Today
    cursor.execute("""
        SELECT COUNT(*) AS present
        FROM attendance
        WHERE attendance_date = CURDATE()
        AND status='Present'
    """)
    present = cursor.fetchone()['present']

    # Absent Today
    absent = total_employees - present

    cursor.close()
    conn.close()

    return render_template(
        "dashboard.html",
        total_employees=total_employees,
        present=present,
        absent=absent
    ) 

# ---------------- EMPLOYEES ---------------- #

@app.route('/employees')
def employees():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM employees ORDER BY emp_id DESC")
    employees = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("employees.html", employees=employees)

#---------------- VIEW EMPLOYEE ---------------- #

@app.route('/view_employee/<int:emp_id>')
def view_employee(emp_id):

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM employees WHERE emp_id=%s", (emp_id,))
    employee = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template("view_employee.html", employee=employee)


# ---------------- REGISTER EMPLOYEE ---------------- #

@app.route('/register_employee', methods=['GET', 'POST'])
def register_employee():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':

        employee_code = request.form['employee_code']
        name = request.form['name']
        gender = request.form['gender']
        dob = request.form['dob']
        phone = request.form['phone']
        email = request.form['email']
        address = request.form['address']
        department_id = request.form['department_id']
        designation = request.form['designation']
        join_date = request.form['join_date']
        check_in = request.form['check_in']
        check_out = request.form['check_out'] 
        basic_salary = request.form['basic_salary']

        cursor.execute("""
        INSERT INTO employees
        (
            employee_code,
            name,
            gender,
            dob,
            phone,
            email,
            address,
            department_id,
            designation,
            join_date,
            check_in,
            check_out,
            basic_salary
        )

        VALUES
        (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)

        """,

        (
            employee_code,
            name,
            gender,
            dob,
            phone,
            email,
            address,
            department_id,
            designation,
            join_date,
            check_in,
            check_out,
            basic_salary
        ))

        conn.commit()

        flash("Employee Registered Successfully!")

        cursor.close()
        conn.close()

        return redirect(url_for('employees'))

    cursor.execute("SELECT COUNT(*) AS total FROM employees")
    count = cursor.fetchone()['total'] + 1

    employee_code = f"EMP{count:03d}"
    
    cursor.close()
    conn.close()

    return render_template(
        "register_employee.html",
        employee_code=employee_code
    )
    return render_template("register_employee.html")



# ---------------- EDIT EMPLOYEE ---------------- #

@app.route('/edit_employee/<int:emp_id>', methods=['GET', 'POST'])
def edit_employee(emp_id):

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':

        employee_code = request.form['employee_code']
        name = request.form['name']
        gender = request.form['gender']
        dob = request.form['dob']
        phone = request.form['phone']
        email = request.form['email']
        address = request.form['address']
        department_id = request.form['department_id']
        designation = request.form['designation']
        join_date = request.form['join_date']
        check_in = request.form['check_in']
        check_out = request.form['check_out']
        basic_salary = request.form['basic_salary']

        cursor.execute("""
            UPDATE employees
            SET
                employee_code=%s,
                name=%s,
                gender=%s,
                dob=%s,
                phone=%s,
                email=%s,
                address=%s,
                department_id=%s,
                designation=%s,
                join_date=%s,
                check_in=%s,
                check_out=%s,
                basic_salary=%s
            WHERE emp_id=%s
        """, (
            employee_code,
            name,
            gender,
            dob,
            phone,
            email,
            address,
            department_id,
            designation,
            join_date,
            check_in,
            check_out,
            basic_salary,
            emp_id
        ))

        conn.commit()

        flash("Employee Updated Successfully!")

        cursor.close()
        conn.close()

        return redirect(url_for('employees'))

    cursor.execute("SELECT * FROM employees WHERE emp_id=%s", (emp_id,))
    employee = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template("edit_employee.html", employee=employee)

#----------------- DELETE EMPLOYEE ---------------- #

@app.route('/delete_employee/<int:emp_id>')
def delete_employee(emp_id):

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM attendance WHERE emp_id=%s", (emp_id,))

    cursor.execute("DELETE FROM employees WHERE emp_id=%s", (emp_id,))

    conn.commit()

    cursor.close()
    conn.close()

    flash("Employee Deleted Successfully!")

    return redirect(url_for('employees'))

# ---------------- ATTENDANCE ---------------- #

@app.route('/attendance', methods=['GET', 'POST'])
def attendance():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Load all employees
    cursor.execute("""
        SELECT emp_id, employee_code, name
        FROM employees
        ORDER BY name
    """)
    employees = cursor.fetchall()

    if request.method == 'POST':

        emp_id = request.form['emp_id']
        attendance_date = request.form['attendance_date']
        check_in = request.form['check_in']
        check_out = request.form['check_out']
        status = request.form['status']

        # Check if attendance is already marked
        cursor.execute("""
            SELECT * FROM attendance
            WHERE emp_id=%s
            AND attendance_date=%s
        """, (emp_id, attendance_date))

        already = cursor.fetchone()

        if already:
            flash("Attendance already marked for this employee today!")
            cursor.close()
            conn.close()
            return redirect(url_for('attendance'))

        # Save attendance
        cursor.execute("""
            INSERT INTO attendance
            (
                emp_id,
                attendance_date,
                check_in,
                check_out,
                status
            )
            VALUES
            (%s,%s,%s,%s,%s)
        """, (
            emp_id,
            attendance_date,
            check_in,
            check_out,
            status
        ))

        conn.commit()

        flash("Attendance Saved Successfully!")

        cursor.close()
        conn.close()

        return redirect(url_for('attendance_history'))

    cursor.close()
    conn.close()

    return render_template("attendance.html", employees=employees)


# ---------------- ATTENDANCE HISTORY ---------------- #

@app.route('/attendance_history')
def attendance_history():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
        a.attendance_id,
        e.employee_code,
        e.name,
        a.attendance_date,
        a.check_in,
        a.check_out,
        a.status

        FROM attendance a

        INNER JOIN employees e

        ON a.emp_id = e.emp_id

        ORDER BY a.attendance_date DESC
    """)

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("attendance_history.html", data=data)

#---------------------------------- ATTENDANCE PDF ---------------- #

@app.route('/attendance_pdf')
def attendance_pdf():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT e.employee_code,
               e.name,
               a.attendance_date,
               a.check_in,
               a.check_out,
               a.status
        FROM attendance a
        JOIN employees e
        ON a.emp_id=e.emp_id
        ORDER BY a.attendance_date DESC
    """)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    response = make_response()

    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=Attendance_Report.pdf"

    pdf = SimpleDocTemplate(response.stream)

    data = [["Employee Code","Name","Date","Check In","Check Out","Status"]]

    for row in rows:

        data.append([
            row['employee_code'],
            row['name'],
            str(row['attendance_date']),
            str(row['check_in']),
            str(row['check_out']),
            row['status']
        ])

    table = Table(data)

    table.setStyle(TableStyle([

        ('BACKGROUND',(0,0),(-1,0),colors.darkred),
        ('TEXTCOLOR',(0,0),(-1,0),colors.gold),
        ('GRID',(0,0),(-1,-1),1,colors.black),
        ('BACKGROUND',(0,1),(-1,-1),colors.beige),
        ('ALIGN',(0,0),(-1,-1),'CENTER')

    ]))

    pdf.build([table])

    return response


# ---------------- REPORTS ---------------- #

@app.route('/reports')
def reports():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Total Employees
    cursor.execute("SELECT COUNT(*) AS total_employees FROM employees")
    total_employees = cursor.fetchone()['total_employees']

    # Present Today
    cursor.execute("""
        SELECT COUNT(*) AS present_today
        FROM attendance
        WHERE attendance_date = CURDATE()
        AND status='Present'
    """)
    present_today = cursor.fetchone()['present_today']

    # Absent Today
    absent_today = total_employees - present_today

    # Total Attendance Records
    cursor.execute("SELECT COUNT(*) AS total_attendance FROM attendance")
    total_attendance = cursor.fetchone()['total_attendance']

    cursor.close()
    conn.close()

    return render_template(
        "reports.html",
        total_employees=total_employees,
        present_today=present_today,
        absent_today=absent_today,
        total_attendance=total_attendance
    )


# ---------------- SALARY ---------------- #

@app.route('/salary')
def salary():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            e.emp_id,
            e.employee_code,
            e.name,
            e.designation,
            e.basic_salary,
            COUNT(
                CASE
                    WHEN a.status='Present'
                    THEN 1
                END
            ) AS present_days
        FROM employees e
        LEFT JOIN attendance a
            ON e.emp_id = a.emp_id
        GROUP BY
            e.emp_id,
            e.employee_code,
            e.name,
            e.designation,
            e.basic_salary
        ORDER BY e.emp_id
    """)

    employees = cursor.fetchall()

    for employee in employees:
        monthly_salary = float(employee['basic_salary'])

        present_days = employee['present_days']

        per_day_salary = monthly_salary / 30

        salary_payable = per_day_salary * present_days

    # Get Bonus & Deduction
        cursor.execute("""
        SELECT bonus, deduction
        FROM bonus_deduction
        WHERE emp_id=%s
        ORDER BY id DESC
        LIMIT 1
        """, (employee['emp_id'],))

        record = cursor.fetchone()

        if record:
            bonus = float(record['bonus'])

            deduction = float(record['deduction'])

        else:
            bonus = 0

            deduction = 0

        net_salary = salary_payable + bonus - deduction

        employee['per_day_salary'] = round(per_day_salary, 2)

        employee['salary_payable'] = round(salary_payable, 2)

        employee['bonus'] = round(bonus, 2)

        employee['deduction'] = round(deduction, 2)

        employee['net_salary'] = round(net_salary, 2)

    cursor.close()
    conn.close()

    return render_template(
        "salary.html",
        employees=employees
    )

#-----------------  SALARY SLIP ---------------- #

@app.route('/salary_slip/<int:emp_id>')
def salary_slip(emp_id):

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            e.emp_id,
            e.employee_code,
            e.name,
            e.designation,
            e.basic_salary,
            COUNT(
                CASE
                    WHEN a.status='Present'
                    THEN 1
                END
            ) AS present_days
        FROM employees e
        LEFT JOIN attendance a
            ON e.emp_id=a.emp_id
        WHERE e.emp_id=%s
        GROUP BY
            e.emp_id,
            e.employee_code,
            e.name,
            e.designation,
            e.basic_salary
    """, (emp_id,))

    employee = cursor.fetchone()

    employee['per_day_salary'] = round(employee['basic_salary'] / 30, 2)

    employee['salary_payable'] = float(round(
        employee['per_day_salary'] * employee['present_days'], 2
    ))

# Get Bonus & Deduction
    cursor.execute("""
    SELECT bonus, deduction
    FROM bonus_deduction
    WHERE emp_id=%s
    ORDER BY id DESC
    LIMIT 1
    """, (emp_id,))

    record = cursor.fetchone()

    if record:
        employee['bonus'] = float(record['bonus'])

        employee['deduction'] = float(record['deduction'])

    else:
        employee['bonus'] = 0

        employee['deduction'] = 0

    employee['net_salary'] = round(
        employee['salary_payable']
        + employee['bonus']
        - employee['deduction'],
        2
    )

    cursor.close()
    conn.close()

    return render_template(
        "salary_slip.html",
        employee=employee
    )

#---------------- DELETE SALARY ---------------- #

@app.route('/delete_salary/<int:emp_id>')
def delete_salary(emp_id):

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM salary_records WHERE emp_id=%s",
        (emp_id,)
    )

    conn.commit()

    cursor.close()
    conn.close()

    flash("Salary Record Deleted Successfully!")

    return redirect(url_for('salary'))

# ---------------- BONUS & DEDUCTION ---------------- #

@app.route('/bonus_deduction', methods=['GET', 'POST'])
def bonus_deduction():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':

        emp_id = request.form['emp_id']
        bonus = request.form['bonus']
        deduction = request.form['deduction']
        remarks = request.form['remarks']

        cursor.execute("""
            INSERT INTO bonus_deduction
            (emp_id, bonus, deduction, remarks)
            VALUES (%s,%s,%s,%s)
        """, (emp_id, bonus, deduction, remarks))

        conn.commit()

        flash("Bonus & Deduction Saved Successfully!")

        return redirect('/bonus_deduction')

    cursor.execute("""
        SELECT emp_id, employee_code, name
        FROM employees
        ORDER BY name
    """)
    employees = cursor.fetchall()

    cursor.execute("""
        SELECT
            b.id,
            e.employee_code,
            e.name,
            b.bonus,
            b.deduction,
            b.remarks
        FROM bonus_deduction b
        INNER JOIN employees e
        ON b.emp_id = e.emp_id
        ORDER BY b.id DESC
    """)
    records = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "bonus_deduction.html",
        employees=employees,
        records=records
    )

#---------------- DELETE BONUS & DEDUCTION ---------------- #

@app.route('/delete_bonus/<int:id>')
def delete_bonus(id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM bonus_deduction WHERE id=%s",
        (id,)
    )

    conn.commit()

    cursor.close()
    conn.close()

    flash("Record Deleted Successfully!")

    return redirect('/bonus_deduction')

#---------------- EDIT BONUS & DEDUCTION ---------------- #

@app.route('/edit_bonus/<int:id>', methods=['GET', 'POST'])
def edit_bonus(id):

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":

        bonus = request.form["bonus"]
        deduction = request.form["deduction"]
        remarks = request.form["remarks"]

        cursor.execute("""
        UPDATE bonus_deduction
        SET bonus=%s,
            deduction=%s,
            remarks=%s
        WHERE id=%s
        """, (bonus, deduction, remarks, id))

        conn.commit()

        cursor.close()
        conn.close()

        flash("Record Updated Successfully!")

        return redirect("/bonus_deduction")

    cursor.execute("""
    SELECT b.*, e.employee_code, e.name
    FROM bonus_deduction b
    JOIN employees e
    ON b.emp_id = e.emp_id
    WHERE b.id=%s
    """, (id,))

    record = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template("edit_bonus.html", record=record)


# ---------------- camera---------------- #

@app.route('/camera')
def camera():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT employee_code, name
        FROM employees
        ORDER BY name
    """)

    employees = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "camera.html",
        employees=employees
    )


# ---------------- GENERATE FRAMES ---------------- #

def generate_frames():

    global camera_message
    global recognised_employee
    global last_person
    global last_time

    while True:

        success, frame = video_camera.read()

        if not success:
            break
        
        global latest_frame
        latest_frame = frame.copy()

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        locations = face_recognition.face_locations(rgb)
        encodings = face_recognition.face_encodings(rgb, locations)

        recognised_employee = ""
        camera_message = "❌ Unknown Person"

        for face_encoding, face_location in zip(encodings, locations):

            name = "Unknown"

            if len(known_encodings) > 0:

                distances = face_recognition.face_distance(
                    known_encodings,
                    face_encoding
                )

                best = np.argmin(distances)

                if distances[best] < 0.5:

                    name = known_names[best]

                    conn = get_db_connection()
                    cursor = conn.cursor(dictionary=True)

                    cursor.execute(
                        """
                        SELECT emp_id, employee_code, name
                        FROM employees
                        WHERE employee_code=%s
                        """,
                        (name,)
                    )

                    employee = cursor.fetchone()

                    print("recognised code:", name)
                    print("recognised employee:", employee)

                    if employee:

                        recognised_employee = employee["name"]

                        emp_id = employee["emp_id"]

                        cursor.execute("""
                            SELECT *
                            FROM attendance
                            WHERE emp_id=%s
                            AND attendance_date=CURDATE()
                        """, (emp_id,))

                        attendance = cursor.fetchone()
                        print("attendance record:", attendance)

                        # ---------------- CHECK-IN ---------------- #

                        if attendance is None:

                            cursor.execute("""
                                INSERT INTO attendance
                                (
                                    emp_id,
                                    attendance_date,
                                    check_in,
                                    status
                                )
                                VALUES
                                (
                                    %s,
                                    CURDATE(),
                                    CURTIME(),
                                    'present'
                                )
                            """, (emp_id,))

                            conn.commit()

                            last_person = employee["employee_code"]
                            last_time = datetime.now()

                            camera_message = (
                                f"✅ Welcome {employee['name']} - "
                                "Check-In Marked Successfully"
                            )

                        # ---------------- CHECK-OUT ---------------- #

                        elif attendance["check_out"] is None:

                            if (
                                last_person == employee["employee_code"]
                                and
                                datetime.now() - last_time <
                                timedelta(seconds=30)
                            ):

                                camera_message = "✅ Check-In Already Marked"

                            else:

                                cursor.execute("""
                                    UPDATE attendance
                                    SET check_out=CURTIME()
                                    WHERE attendance_id=%s
                                """, (attendance["attendance_id"],))

                                conn.commit()

                                last_person = employee["employee_code"]
                                last_time = datetime.now()

                                camera_message = (
                                    f"✅ Goodbye {employee['name']} - "
                                    "Check-Out Marked Successfully"
                                )

                        else:

                            camera_message = "⚠ Attendance Already Completed"

                    cursor.close()
                    conn.close()

            top, right, bottom, left = face_location

            cv2.rectangle(
                frame,
                (left, top),
                (right, bottom),
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                name,
                (left, top - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

        ret, buffer = cv2.imencode(".jpg", frame)

        frame = buffer.tobytes()

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' +
            frame +
            b'\r\n'
        )

#----------------- CAPTURE FACE ---------------- #

@app.route('/capture_face', methods=['POST'])
def capture_face():

    global latest_frame

    employee_code = request.form['employee_code']

    if latest_frame is None:

        return jsonify({
            "message": "❌ Camera not ready"
        })

    folder = "static/uploads/faces"

    if not os.path.exists(folder):
        os.makedirs(folder)

    filename = os.path.join(folder, employee_code + ".jpg")

    cv2.imwrite(filename, latest_frame)

    load_faces()

    return jsonify({
        "message": "✅ Face Captured Successfully"
    })

#----------------- video_feed ---------------- #

@app.route("/video_feed")
def video_feed():

    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

#------------------ camera_message ---------------- #

@app.route("/camera_message")
def get_camera_message():

    return jsonify({
        "message": camera_message,
        "employee": recognised_employee
        })
#---------------- DELETE ATTENDANCE ---------------- #

@app.route('/delete_attendance/<int:attendance_id>')
def delete_attendance(attendance_id):

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM attendance WHERE attendance_id=%s",
        (attendance_id,)
    )

    conn.commit()

    cursor.close()
    conn.close()

    flash("Attendance Deleted Successfully!")

    return redirect(url_for('attendance_history'))

# ---------------- LOGOUT ---------------- #

@app.route('/logout')
def logout():

    session.clear()

    flash("Logged out successfully!")

    return redirect(url_for('login'))


# ---------------- RUN ---------------- #

if __name__ == "__main__":
    app.run(debug=True)                                                                                                   