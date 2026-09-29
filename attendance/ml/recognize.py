import cv2
import json
import numpy as np
import tensorflow as tf

from pathlib import Path
from django.conf import settings
from attendance.models import Student


def run_face_recognition():

    # --------------------------------
    # Model paths
    # --------------------------------

    model_path = (
        Path(settings.BASE_DIR)
        / "ml_models"
        / "face_recognition_model.keras"
    )

    classes_path = (
        Path(settings.BASE_DIR)
        / "ml_models"
        / "class_names.json"
    )


    # --------------------------------
    # Check model files
    # --------------------------------

    if not model_path.exists():
        print("Trained model not found.")
        return

    if not classes_path.exists():
        print("class_names.json not found.")
        return


    # --------------------------------
    # Load CNN
    # --------------------------------

    model = tf.keras.models.load_model(
        model_path
    )


    # --------------------------------
    # Load class names
    # --------------------------------

    with open(classes_path, "r") as file:
        class_names = json.load(file)


    print(
        "Loaded classes:",
        class_names
    )


    # --------------------------------
    # Load Haar Cascade
    # --------------------------------

    face_detector = cv2.CascadeClassifier(
        cv2.data.haarcascades
        + "haarcascade_frontalface_default.xml"
    )


    if face_detector.empty():
        print("Unable to load Haar Cascade.")
        return


    # --------------------------------
    # Open webcam
    # --------------------------------

    camera = cv2.VideoCapture(
        0,
        cv2.CAP_AVFOUNDATION
    )


    if not camera.isOpened():
        print("Unable to open webcam.")
        return


    threshold = 80


    # --------------------------------
    # Webcam loop
    # --------------------------------

    while True:

        success, frame = camera.read()

        if not success:
            print("Unable to read frame.")
            break


        # Convert to grayscale
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


        # --------------------------------
        # Process each face
        # --------------------------------

        for x, y, width, height in faces:

            # Crop face
            face_image = gray_frame[
                y:y + height,
                x:x + width
            ]


            # Resize
            face_image = cv2.resize(
                face_image,
                (128, 128)
            )


            # Add channel dimension
            face_input = np.expand_dims(
                face_image,
                axis=-1
            )


            # Add batch dimension
            face_input = np.expand_dims(
                face_input,
                axis=0
            )


            # CNN prediction
            predictions = model.predict(
                face_input,
                verbose=0
            )


            predicted_index = np.argmax(
                predictions[0]
            )


            student_id = class_names[
                predicted_index
            ]


            confidence = (
                predictions[0][predicted_index]
                * 100
            )


            # Default values
            display_name = "Unknown"

            display_id = ""


            # --------------------------------
            # Check confidence
            # --------------------------------

            if confidence >= threshold:

                try:

                    student = Student.objects.get(
                        student_id=student_id
                    )

                    display_name = student.name

                    display_id = student.student_id


                except Student.DoesNotExist:

                    display_name = (
                        "Student Not Found"
                    )


            # --------------------------------
            # Rectangle
            # --------------------------------

            if confidence >= threshold:

                color = (0, 255, 0)

            else:

                color = (0, 0, 255)


            cv2.rectangle(
                frame,
                (x, y),
                (x + width, y + height),
                color,
                2
            )


            # --------------------------------
            # Name
            # --------------------------------

            cv2.putText(
                frame,
                display_name,
                (x, y - 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2
            )


            # --------------------------------
            # Student ID + confidence
            # --------------------------------

            if display_id:

                text = (
                    f"{display_id} - "
                    f"{confidence:.2f}%"
                )

            else:

                text = (
                    f"Confidence: "
                    f"{confidence:.2f}%"
                )


            cv2.putText(
                frame,
                text,
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2
            )


        # Show webcam
        cv2.imshow(
            "Django Face Recognition",
            frame
        )


        # q = quit
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break


    camera.release()

    cv2.destroyAllWindows()