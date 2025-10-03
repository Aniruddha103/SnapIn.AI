import mysql.connector
import os

# ------------------ Database Connection ------------------
def create_connection():
    try:
        conn = mysql.connector.connect(
            host="localhost",  # Replace with server IP if remote
            user="root",
            password="",
            database="student"
        )
        return conn
    except mysql.connector.Error as e:
        print(f"DB Connection Error: {e}")
        return None

# ------------------ Insert Image Function ------------------
def insert_student_image(student_id, name, image_path):
    connection = create_connection()
    if not connection:
        return
    try:
        cursor = connection.cursor()
        with open(image_path, "rb") as f:
            image_blob = f.read()
        query = "INSERT INTO student_images (student_id, name, image) VALUES (%s, %s, %s)"
        cursor.execute(query, (student_id, name, image_blob))
        connection.commit()
        print(f"Inserted {name} ({student_id}) successfully!")
    except mysql.connector.Error as e:
        print(f"Error inserting {name}: {e}")
    finally:
        cursor.close()
        connection.close()

# ------------------ Insert All Images from Folder ------------------
images_folder = "E:/IEEE hackathon/Code/images/archive/faces"

for filename in os.listdir(images_folder):
    if filename.lower().endswith((".jpg", ".jpeg", ".png")):
        student_id = int(os.path.splitext(filename)[0])
        name = os.path.splitext(filename)[0]  # You can replace with actual names if needed
        image_path = os.path.join(images_folder, filename)
        insert_student_image(student_id, name, image_path)
