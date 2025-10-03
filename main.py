import threading
import cv2
import numpy as np
import face_recognition
from datetime import datetime, time, timedelta
import mysql.connector
import time as t
import os

# ------------------ Configuration ------------------
# The image files should be named after the student's ID, e.g., "1.jpg", "42.png".
STUDENT_IMAGE_FOLDER = "E:/IEEE hackathon/Code/images/archive/faces/Student_Images/TY A"

# Global dictionary to control camera threads individually
# The key will be timetable_id, the value will be True/False
running_status = {}

# ------------------ Database Functions ------------------

def create_connection():
    """Establishes connection to the MySQL database."""
    try:
        connection = mysql.connector.connect(
            host="dhanwardhan.com",
            user="dhanwusu_AuAtt_Admin",
            password="Dhan_AuAtt@321",
            database="dhanwusu_AuAtt_sys_db"
        )
        if connection.is_connected():
            return connection
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def mark_attendance_in_db(student_id, timetable_id):
    """Inserts an attendance record into the database."""
    connection = create_connection()
    if not connection:
        return
    try:
        cursor = connection.cursor()
        today_date = datetime.now().date()
        
        check_query = "SELECT attendance_id FROM Attendance WHERE student_id = %s AND timetable_id = %s AND date = %s"
        cursor.execute(check_query, (student_id, timetable_id, today_date))
        if cursor.fetchone():
            return

        insert_query = "INSERT INTO Attendance (student_id, timetable_id, date, status) VALUES (%s, %s, %s, %s)"
        values = (student_id, timetable_id, today_date, 'Present')
        cursor.execute(insert_query, values)
        connection.commit()
        
        print(f"Attendance MARKED for Student ID: {student_id}, Timetable ID: {timetable_id} on {today_date}")

    except mysql.connector.Error as e:
        print(f"Database Error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# ------------------ Fetch Faces from Image Folder ------------------

def load_faces_from_folder(folder_path):
    """Loads images from a folder, encodes faces, and uses filenames as student IDs."""
    known_face_encodings = []
    known_face_ids = []

    if not os.path.isdir(folder_path):
        print(f"Error: Image folder not found at '{folder_path}'")
        return known_face_encodings, known_face_ids

    print(f"Loading faces from {folder_path}...")
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            image_path = os.path.join(folder_path, filename)
            student_id = os.path.splitext(filename)[0]
            try:
                image = face_recognition.load_image_file(image_path)
                encodings = face_recognition.face_encodings(image)
                if encodings:
                    known_face_encodings.append(encodings[0])
                    known_face_ids.append(student_id)
                else:
                    print(f"Warning: No faces found in {filename}. Skipping.")
            except Exception as e:
                print(f"Error processing image {filename}: {e}")
    print(f"Loaded {len(known_face_ids)} known faces from the folder.")
    return known_face_encodings, known_face_ids

# ------------------ Fetch Timetable from DB ------------------

def fetch_timetable_for_today():
    """Fetches today's timetable by joining Timetable, Division, and Year tables."""
    connection = create_connection()
    if not connection: return []
    timetable = []
    try:
        day_of_week = datetime.now().strftime('%a')
        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT 
                tt.timetable_id, tt.start_time, tt.end_time, tt.camera_url,
                CONCAT(y.year_name, ' - Div ', d.division_name) AS class_name
            FROM Timetable tt
            JOIN Division d ON tt.division_id = d.division_id
            JOIN Year y ON d.year_id = y.year_id
            WHERE tt.day_of_week = %s
        """
        cursor.execute(query, (day_of_week,))
        rows = cursor.fetchall()
        for row in rows:
            timetable.append({
                "timetable_id": row["timetable_id"], "class_name": row["class_name"],
                "start": row["start_time"], "end": row["end_time"],
                "camera_url": row["camera_url"]
            })
    except mysql.connector.Error as e:
        print(f"Error fetching timetable: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
    return timetable

# ------------------ Camera Thread (MODIFIED for multiple classes) ------------------

def run_camera(camera_url, class_name, timetable_id):
    """Main function to run a camera for a SINGLE class, checking its own running status."""
    global running_status
    known_face_encodings, known_face_ids = load_faces_from_folder(STUDENT_IMAGE_FOLDER)
    if not known_face_ids:
        print(f"No known faces loaded. Stopping camera thread for {class_name}.")
        running_status[timetable_id] = False
        return
        
    video_capture = cv2.VideoCapture(camera_url)

    if not video_capture.isOpened():
        print(f"Error: Cannot access camera at {camera_url} for {class_name}")
        running_status[timetable_id] = False
        return

    print(f"✅ Camera started for {class_name} (Timetable ID: {timetable_id})")

    # The main loop now checks its OWN status in the shared dictionary
    while running_status.get(timetable_id, False):
        ret, frame = video_capture.read()
        if not ret:
            t.sleep(0.1)
            continue
            
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.6)
            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            
            if len(face_distances) == 0: continue

            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                student_id = known_face_ids[best_match_index]
                mark_attendance_in_db(int(student_id), timetable_id)

    video_capture.release()
    cv2.destroyAllWindows()
    print(f"🛑 Camera stopped for {class_name}.")


# ------------------ Attendance Scheduler (MODIFIED for multiple classes) ------------------

def attendance_scheduler():
    global running_status
    attendance_duration = timedelta(minutes=10)
    
    run_start_time = time(9, 0)
    run_end_time = time(18, 0)

    timetable = []
    last_fetched_date = None

    print("✅ Attendance System Started. Waiting for operational hours (9 AM - 6 PM).")

    while True:
        now = datetime.now()
        
        if run_start_time <= now.time() <= run_end_time:
            if last_fetched_date != now.date():
                print(f"🌞 Operational hours started. Fetching timetable for {now.date()}...")
                timetable = fetch_timetable_for_today()
                last_fetched_date = now.date()
                if not timetable: print("No classes scheduled for today.")
                else: print("Today's Timetable:", timetable)
            
            if timetable:
                # --- START/CHECK PHASE: Iterate through all classes ---
                for cls in timetable:
                    class_id = cls["timetable_id"]
                    class_start = datetime.combine(now.date(), cls["start"])
                    class_end = datetime.combine(now.date(), cls["end"])
                    
                    is_active = class_start <= now < class_end
                    
                    # If class is currently active
                    if is_active:
                        class_start_time = datetime.combine(now.date(), cls["start"])
                        attendance_window_end = class_start_time + attendance_duration
                        
                        # Check if class is in attendance window AND not already running
                        if now < attendance_window_end and not running_status.get(class_id, False):
                            running_status[class_id] = True
                            thread = threading.Thread(target=run_camera, args=(
                                cls["camera_url"], cls["class_name"], class_id
                            ), daemon=True)
                            thread.start()
                    
                    # If class is NOT active, but we have a running thread for it, stop it.
                    elif not is_active and running_status.get(class_id, False):
                        print(f"Class session for Timetable ID {class_id} has ended.")
                        running_status[class_id] = False # Signal thread to stop

            t.sleep(5) 
            
        else:
            # --- Outside operational hours ---
            if any(running_status.values()):
                print("🌙 Operational hours ended. Stopping all camera processes.")
                for key in running_status:
                    running_status[key] = False # Signal all threads to stop
            
            if last_fetched_date is not None:
                print("Resetting daily schedule. Ready for tomorrow.")
                last_fetched_date = None
                timetable = []
                running_status.clear() # Clear the status dictionary for the next day

            t.sleep(600)

# ------------------ Main Execution ------------------
if __name__ == "__main__":
    attendance_scheduler()