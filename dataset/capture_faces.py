import cv2
import os


# Take student information
student_id = input("Enter Student ID: ")
student_name = input("Enter Student Name: ")


# Create folder name
folder_name = f"{student_name}_{student_id}"


# Complete dataset folder path
dataset_path = os.path.join(
    "dataset",
    folder_name
)


# Create folder if it does not exist
os.makedirs(
    dataset_path,
    exist_ok=True
)


# Load Haar Cascade face detector
face_detector = cv2.CascadeClassifier(
    cv2.data.haarcascades +
    "haarcascade_frontalface_default.xml"
)


# Open webcam
camera = cv2.VideoCapture(0)


if not camera.isOpened():
    print("Unable to open webcam.")
    exit()


image_count = 0

max_images = 100


while True:

    # Capture webcam frame
    success, frame = camera.read()

    if not success:
        print("Unable to read frame.")
        break


    # Convert frame to grayscale
    gray_frame = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2GRAY
    )


    # Detect faces
    faces = face_detector.detectMultiScale(
        gray_frame,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(100, 100)
    )


    for x, y, width, height in faces:

        # Draw rectangle
        cv2.rectangle(
            frame,
            (x, y),
            (x + width, y + height),
            (0, 255, 0),
            2
        )


        # Crop only face
        face_image = gray_frame[
            y:y + height,
            x:x + width
        ]


        # Resize face
        face_image = cv2.resize(
            face_image,
            (200, 200)
        )


        # Increase image count
        image_count += 1


        # Create image filename
        image_name = f"face_{image_count:03d}.jpg"


        # Complete image path
        image_path = os.path.join(
            dataset_path,
            image_name
        )


        # Save face image
        cv2.imwrite(
            image_path,
            face_image
        )


        # Display image count
        cv2.putText(
            frame,
            f"Captured: {image_count}/{max_images}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )


    # Show webcam
    cv2.imshow(
        "Capture Student Faces",
        frame
    )


    # Stop when 30 images captured
    if image_count >= max_images:
        break


    # Press q manually to stop
    if cv2.waitKey(100) & 0xFF == ord("q"):
        break


camera.release()

cv2.destroyAllWindows()


print(
    f"{image_count} face images saved successfully."
)