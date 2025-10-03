import os
from PIL import Image

# ------------------ Configuration ------------------
# 📁 Set the path to the folder with your original student images.
SOURCE_FOLDER = "E:/IEEE hackathon/Code/images/archive/faces/Student_Images/TY B"

# 📁 Set the path where the converted RGB images will be saved.
DESTINATION_FOLDER = "E:/IEEE hackathon/Code/images/archive/faces/Student_Images/TY B"
# ----------------------------------------------------

def convert_images_to_rgb(input_dir, output_dir):
    """
    Scans a directory for images, converts them to 3-channel RGB format,
    and saves them to an output directory.
    """
    # 1. Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        print(f"Creating destination directory: {output_dir}")
        os.makedirs(output_dir)

    # 2. Check if the source directory exists
    if not os.path.isdir(input_dir):
        print(f"❌ Error: Source directory not found at '{input_dir}'")
        return

    print(f"Starting image conversion from '{input_dir}' to '{output_dir}'...")
    
    converted_count = 0
    skipped_count = 0

    # 3. Loop through all files in the source directory
    for filename in os.listdir(input_dir):
        # Construct the full path of the source image
        source_path = os.path.join(input_dir, filename)

        # Check if it's a file and a supported image type
        if os.path.isfile(source_path) and filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
            try:
                # Open the image using Pillow
                with Image.open(source_path) as img:
                    # Convert the image to RGB mode
                    # This handles grayscale, RGBA (with transparency), etc.
                    rgb_img = img.convert('RGB')
                    
                    # Construct the full path for the destination image
                    # It's best to save in a standard format like JPEG
                    base_filename, _ = os.path.splitext(filename)
                    destination_path = os.path.join(output_dir, f"{base_filename}.jpg")
                    
                    # Save the converted image
                    rgb_img.save(destination_path, 'jpeg')
                    
                    print(f"✅ Converted: {filename} -> {os.path.basename(destination_path)}")
                    converted_count += 1

            except Exception as e:
                print(f"❌ Error processing {filename}: {e}")
                skipped_count += 1
        else:
            # This handles non-image files or subdirectories
            print(f"⏩ Skipped non-image file: {filename}")
            skipped_count += 1

    print("\n--- Conversion Summary ---")
    print(f"Total images converted: {converted_count}")
    print(f"Total files skipped: {skipped_count}")
    print("--------------------------")


# ------------------ Main Execution ------------------
if __name__ == "__main__":
    convert_images_to_rgb(SOURCE_FOLDER, DESTINATION_FOLDER)
