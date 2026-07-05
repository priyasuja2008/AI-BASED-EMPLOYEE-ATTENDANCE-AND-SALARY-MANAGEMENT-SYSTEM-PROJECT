import face_recognition
import cv2
import os
import mysql.connector
from datetime import datetime

# ---------------- DATABASE ---------------- #

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Priya123@",
        database="attendance_system"
    )

# ---------------- LOAD REGISTERED FACES ---------------- #

known_encodings = []
known_names = []

path = "static/uploads/faces"

if not os.path.exists(path):
    os.makedirs(path)

for file in os.listdir(path):

    if file.lower().endswith((".jpg", ".jpeg", ".png")):

        image_path = os.path.join(path, file)

        image = face_recognition.load_image_file(image_path)

        encodings = face_recognition.face_encodings(image)

        if len(encodings) > 0:

            known_encodings.append(encodings[0])

            known_names.append(os.path.splitext(file)[0])

print("Loaded Faces :", known_names)

# ---------------- CAMERA ---------------- #

camera = cv2.VideoCapture(0)

if not camera.isOpened():

    print("Unable to Open Camera")

    exit()

marked_today = []

print("AI Attendance Started...")
# ---------------- FACE RECOGNITION ---------------- #

while True:

    success, frame = camera.read()

    if not success:
        break

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb)

    face_encodings = face_recognition.face_encodings(
        rgb,
        face_locations
    )

    for face_encoding, face_location in zip(
        face_encodings,
        face_locations
    ):

        matches = face_recognition.compare_faces(
            known_encodings,
            face_encoding
        )

        name = "Unknown"

        face_distances = face_recognition.face_distance(
        known_encodings,
        face_encoding
    )

    if len(face_distances) > 0:
        best_match = face_distances.argmin()

        if face_distances[best_match] < 0.5:
            name = known_names[best_match]

            conn = get_db_connection()

            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT emp_id,name
                FROM employees
                WHERE employee_code=%s
            """,(name,))

            employee = cursor.fetchone()

            if employee:

                emp_id = employee["emp_id"]

                employee_name = employee["name"]

                today = datetime.now().date()

                if emp_id not in marked_today:

                    cursor.execute("""
                        SELECT *
                        FROM attendance
                        WHERE emp_id=%s
                        AND attendance_date=%s
                    """,(emp_id,today))

                    already = cursor.fetchone()

                    if not already:

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
                                %s,
                                NOW(),
                                'Present'
                            )
                        """,(emp_id,today))

                        conn.commit()

                        marked_today.append(emp_id)

                        print(employee_name,"Attendance Marked")

            cursor.close()

            conn.close()

        top,right,bottom,left = face_location

        color = (0,255,0)

        if name == "Unknown":

            color = (0,0,255)

        cv2.rectangle(
            frame,
            (left,top),
            (right,bottom),
            color,
            2
        )

        cv2.putText(
            frame,
            name,
            (left,top-10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            color,
            2
        )

    cv2.imshow(
        "AI Attendance System",
        frame
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()

cv2.destroyAllWindows()