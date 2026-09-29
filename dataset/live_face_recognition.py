import cv2
import json
import numpy as np
import tensorflow as tf


# --------------------------------
# 1. Load trained CNN model
# --------------------------------

model = tf.keras.models.load_model(
    "face_recognition_model.keras"
)


# --------------------------------
# 2. Load student/class names
# --------------------------------

with open("class_names.json", "r") as file:
    class_names = json.load(file)


print("Classes:", class_names)


# --------------------------------
# 3. Load Haar Cascade
# --------------------------------

face_detector = cv2.CascadeClassifier(
    cv2.data.haarcascades +
    "haarcascade_frontalface_default.xml"
)


# --------------------------------
# 4. Open webcam
# --------------------------------

camera = cv2.VideoCapture(0)


if not camera.isOpened():

    print("Unable to open webcam.")

    exit()


# Recognition threshold
threshold = 80


# --------------------------------
# 5. Start webcam loop
# --------------------------------

while True:

    success, frame = camera.read()


    if not success:

        print("Unable to read frame.")

        break


    # --------------------------------
    # Convert frame to grayscale
    # --------------------------------

    gray_frame = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2GRAY
    )


    # --------------------------------
    # Detect faces
    # --------------------------------

    faces = face_detector.detectMultiScale(
        gray_frame,
        scaleFactor=1.1,
        minNeighbors=8,
        minSize=(100, 100)
    )


    # --------------------------------
    # Process every detected face
    # --------------------------------

    for x, y, width, height in faces:

        # Crop face
        face_image = gray_frame[
            y:y + height,
            x:x + width
        ]


        # Resize to CNN input size
        face_image = cv2.resize(
            face_image,
            (128, 128)
        )


        # Add grayscale channel
        face_input = np.expand_dims(
            face_image,
            axis=-1
        )


        # Add batch dimension
        face_input = np.expand_dims(
            face_input,
            axis=0
        )


        # --------------------------------
        # CNN prediction
        # --------------------------------

        predictions = model.predict(
            face_input,
            verbose=0
        )


        # Find largest prediction
        predicted_index = np.argmax(
            predictions[0]
        )


        # Student name
        predicted_student = class_names[
            predicted_index
        ]


        # Confidence percentage
        confidence = (
            predictions[0][predicted_index]
            * 100
        )


        # --------------------------------
        # Check confidence
        # --------------------------------

        if confidence >= threshold:

            label = (
                f"{predicted_student} "
                f"{confidence:.2f}%"
            )

        else:

            label = (
                f"Unknown "
                f"{confidence:.2f}%"
            )

        print(predicted_student)
        # --------------------------------
        # Draw rectangle
        # --------------------------------

        cv2.rectangle(
            frame,
            (x, y),
            (x + width, y + height),
            (0, 255, 0),
            2
        )


        # --------------------------------
        # Display student name
        # --------------------------------

        cv2.putText(
            frame,
            label,
            (x, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )


    # --------------------------------
    # Display webcam
    # --------------------------------

    cv2.imshow(
        "Face Recognition",
        frame
    )


    # Press q to stop
    if cv2.waitKey(1) & 0xFF == ord("q"):

        break


# --------------------------------
# Release camera
# --------------------------------

camera.release()

cv2.destroyAllWindows()