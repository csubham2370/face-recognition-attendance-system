import cv2
import json
import numpy as np
import tensorflow as tf

from pathlib import Path
from django.conf import settings


MODEL_PATH = (Path(settings.BASE_DIR) / "ml_models" / "face_recognition_model.keras")

CLASS_NAMES_PATH = (Path(settings.BASE_DIR) / "ml_models" / "class_names.json")

# Load model only once
model = tf.keras.models.load_model(MODEL_PATH)

# Load class names only once
with open(CLASS_NAMES_PATH, "r") as file:
    class_names = json.load(file)

# Load Haar Cascade when the installed OpenCV build provides it. Some newer
# builds omit CascadeClassifier, so prediction also supports a centered crop.
cascade_classifier = getattr(cv2, "CascadeClassifier", None)
face_detector = (
    cascade_classifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    if cascade_classifier is not None
    else None
)

def reload_model():

    global model
    global class_names

    # Reload newly trained model
    model = tf.keras.models.load_model(MODEL_PATH)
    # Reload updated student classes
    with open(CLASS_NAMES_PATH,"r") as file:

        class_names = json.load(file)

    print("Face recognition model reloaded successfully.")

    
def predict_face(image):
    try:
        current_class_names = json.loads(CLASS_NAMES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"success": False, "message": "The recognition classes are unavailable. Train the model again."}

    # Convert BGR image to grayscale
    gray_image = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)

    if face_detector is not None:
        faces = face_detector.detectMultiScale(gray_image,scaleFactor=1.1,minNeighbors=5,minSize=(100, 100))
        if len(faces) == 0:
            return {"success": False, "message": "No face detected. Center your face and try again."}
        if len(faces) > 1:
            return {"success": False, "message": "Multiple faces detected. Only one person may be visible."}
        x, y, width, height = faces[0]
        face_image = gray_image[y:y + height, x:x + width]
    else:
        image_height, image_width = gray_image.shape
        crop_size = min(image_height, image_width)
        x = (image_width - crop_size) // 2
        y = (image_height - crop_size) // 2
        face_image = gray_image[y:y + crop_size, x:x + crop_size]

    # Resize for CNN
    face_image = cv2.resize(face_image,(128, 128))

    # Add channel
    face_input = np.expand_dims(face_image,axis=-1)

    # Add batch
    face_input = np.expand_dims(face_input,axis=0)

    # Prediction
    predictions = model.predict(face_input,verbose=0)

    if len(predictions[0]) != len(current_class_names):
        return {
            "success": False,
            "message": "Student data changed after the last training. Ask an administrator to train the model again.",
        }

    predicted_index = np.argmax(predictions[0])

    student_id = current_class_names[predicted_index]

    confidence = float(predictions[0][predicted_index]* 100)

    threshold = 80

    if confidence < threshold:

        return {
            "success": False,
            "message": "Unknown Person",
            "confidence": confidence
        }


    return {
        "success": True,
        "student_id": student_id,
        "confidence": confidence
    }
