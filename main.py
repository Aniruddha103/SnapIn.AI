import threading
import cv2
import numpy as np
import face_recognition
from datetime import datetime, time, timedelta
import mysql.connector
import os
import time as t

# ------------------ Attendance System ------------------
images_dir = "C:/Users/Aniruddha/OneDrive/Pictures/Camera Roll/"

images_path = {}
student_ids = {}

for filename in os.listdir(images_dir):
    if filename.lower().endswith((".jpg", ".jpeg", ".png")):
        roll_no = os.path.splitext(filename)[0]
        images_path[roll_no] = os.path.join(images_dir, filename)
        student_ids[roll_no] = int(roll_no)

marked_students = set()
running = False 

# ------------------ Database Functions ------------------
def create_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="student"
        )
        if connection.is_connected():
            print("Connected to MySQL database")
        return connection
    except mysql.connector.Error as e:
        print(f"Error: {e}")
        return None

def insert_student(student_id, roll_no):
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            query = "INSERT INTO students (id, name, timestamp) VALUES (%s, %s, %s)"
            cursor.execute(query, (student_id, roll_no, now))
            connection.commit()
            print(f"Inserted {roll_no} (ID: {student_id}) at {now}")
        except mysql.connector.Error as e:
            print(f"Error: {e}")
        finally:
            cursor.close()
            connection.close()

def mark_attendance(roll_no):
    if roll_no in student_ids and roll_no not in marked_students:
        student_id = student_ids[roll_no]
        insert_student(student_id, roll_no)
        marked_students.add(roll_no)

def load_known_faces_and_names():
    known_face_encodings = []
    known_face_names = []
    for roll_no, path in images_path.items():
        if not os.path.exists(path):
            continue
        image = face_recognition.load_image_file(path)
        encodings = face_recognition.face_encodings(image)
        if encodings:
            known_face_encodings.append(encodings[0])
            known_face_names.append(roll_no)
    return known_face_encodings, known_face_names

# ------------------ Fetch Timetable from DB ------------------
def fetch_timetable_from_db():
    connection = create_connection()
    if not connection:
        return []

    timetable = []
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT class_name, start_time, end_time FROM timetable")
        rows = cursor.fetchall()
        for row in rows:
            timetable.append({
                "class_name": row["class_name"],
                "start": row["start_time"],
                "end": row["end_time"]
            })
    except mysql.connector.Error as e:
        print(f"Error fetching timetable: {e}")
    finally:
        cursor.close()
        connection.close()
    
    return timetable

# Load timetable once at start
timetable = fetch_timetable_from_db()

# ------------------ Camera Thread ------------------
def run_camera():
    global running
    known_face_encodings, known_face_names = load_known_faces_and_names()
    video_capture = cv2.VideoCapture(0)

    # For CCTV cameras example: 
    #video_capture = cv2.VideoCapture("rtsp://username:password@camera_ip:554/stream1")

    if not video_capture.isOpened():
        print("Cannot access camera")
        running = False
        return

    while running:
        ret, frame = video_capture.read()
        if not ret:
            continue
        small_frame = cv2.resize(frame, (0,0), fx=0.5, fy=0.5)
        face_locations = face_recognition.face_locations(small_frame)
        face_encodings = face_recognition.face_encodings(small_frame, face_locations)
        for face_encoding, face_location in zip(face_encodings, face_locations):
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.5)
            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            if len(face_distances) == 0:
                continue
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                roll_no = known_face_names[best_match_index]
                mark_attendance(roll_no)
                top, right, bottom, left = [v*2 for v in face_location]
                cv2.rectangle(frame, (left, top), (right, bottom), (0,255,0), 2)
                cv2.putText(frame, roll_no, (left, top-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,0), 2)
        cv2.imshow("Attendance", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    video_capture.release()
    cv2.destroyAllWindows()
    running = False

# ------------------ Attendance Scheduler ------------------
def attendance_scheduler():
    global running
    attendance_duration = timedelta(minutes=10)  # Take attendance for first 10 minutes

    while True:
        now = datetime.now()
        class_running = False

        for cls in timetable:
            class_start = datetime.combine(now.date(), cls["start"])
            class_end = datetime.combine(now.date(), cls["end"])

            if class_start <= now < class_end:
                class_running = True

                # Start camera only if within first 10 mins
                if not running and now < class_start + attendance_duration:
                    running = True
                    thread = threading.Thread(target=run_camera, daemon=True)
                    thread.start()
                    print(f"{cls['class_name']} started at {now.time()}, taking attendance for 10 mins...")
                break  # Only one class at a time

        # Stop camera if running and either 10 mins passed or class ended
        if running:
            current_class = next((cls for cls in timetable if datetime.combine(now.date(), cls["start"]) <= now < datetime.combine(now.date(), cls["end"])), None)
            if not current_class or now >= datetime.combine(now.date(), current_class["start"]) + attendance_duration:
                running = False
                print(f"Attendance window ended at {now.time()}, camera stopped.")

        t.sleep(5)
