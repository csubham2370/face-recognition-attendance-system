import cv2
import os
import time

def capture_student_faces(student_id):

    dataset_folder = "dataset"
    student_folder = os.path.join(dataset_folder,student_id)
    os.makedirs(student_folder,exist_ok=True)

    # Load Haar Cascade
    face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    
    if face_detector.empty():
        print("Face detector could not be loaded.")
        return False

    # macOS camera backend
    camera = cv2.VideoCapture(0,cv2.CAP_AVFOUNDATION)

    if not camera.isOpened():
        print("Unable to open webcam.")
        return False

    image_count = 0
    max_images = 100
    start_time = time.time()
    # Maximum 30 seconds
    timeout = 30

    try:

        while image_count < max_images:
            # Stop if taking too long
            if time.time() - start_time > timeout:
                print("Face capture timed out.")
                break

            success, frame = camera.read()

            if not success:
                print("Unable to read camera frame.")
                break

            gray_frame = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)

            faces = face_detector.detectMultiScale(gray_frame,scaleFactor=1.1, minNeighbors=5,minSize=(100, 100))

            # Save only when exactly one face exists
            if len(faces) == 1:

                x, y, width, height = faces[0]

                face_image = gray_frame[ y:y + height,x:x + width]

                if face_image.size == 0:
                    continue

                face_image = cv2.resize(face_image,(200, 200))
                image_count += 1
                image_name = (f"face_{image_count:03d}.jpg")
                
                image_path = os.path.join(student_folder, image_name)
                saved = cv2.imwrite( image_path,face_image )

                if saved:
                    print(f"Captured: " f"{image_count}/{max_images}")

                # Small delay between images
                time.sleep(0.1)


    except Exception as error:
        print("Face capture error:",error)

        return False

    finally:
        camera.release()

    print(f"Total images captured: " f"{image_count}")
    return image_count >= max_images