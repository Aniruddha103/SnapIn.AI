import os

# Folder containing images
folder = r"E:/IEEE hackathon/Code/images/archive/faces/Student_Images/TY B"


# Starting number for renaming
start_num = 234051

# Get all jpg files in the folder
files = [f for f in os.listdir(folder) if f.lower().endswith(".jpg")]

# Sort files to maintain order (optional)
files.sort()

for i, filename in enumerate(files):
    old_path = os.path.join(folder, filename)
    new_filename = f"{start_num + i}.jpg"
    new_path = os.path.join(folder, new_filename)
    os.rename(old_path, new_path)
    print(f"Renamed {filename} -> {new_filename}")
