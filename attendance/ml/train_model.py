import json
import shutil
import sys
import tempfile
from pathlib import Path

import tensorflow as tf

from django.conf import settings
from attendance.models import Student


class TerminalMetricsCallback(tf.keras.callbacks.Callback):
    """Print epoch metrics reliably when training is started by a Django view."""

    def __init__(self, total_epochs):
        super().__init__()
        self.total_epochs = total_epochs

    def on_epoch_end(self, epoch, logs=None):
        logs = logs or {}
        metrics = []

        for name in ("loss", "accuracy", "val_loss", "val_accuracy"):
            value = logs.get(name)
            if value is not None:
                metrics.append(f"{name}: {value:.4f}")

        message = f"Epoch {epoch + 1}/{self.total_epochs} - " + " - ".join(metrics)
        output = sys.__stdout__ if sys.__stdout__ is not None else sys.stdout
        print(message, file=output, flush=True)


def train_face_model():

    # -----------------------------
    # Paths
    # -----------------------------

    dataset_path = (Path(settings.BASE_DIR)/ "dataset")

    model_folder = (Path(settings.BASE_DIR) / "ml_models")

    model_folder.mkdir(exist_ok=True)

    model_path = (model_folder / "face_recognition_model.keras")

    classes_path = (model_folder / "class_names.json")

    # Build an isolated training dataset containing only current database
    # students. Old/orphan folders must never become prediction classes.
    training_workspace = tempfile.TemporaryDirectory(prefix="face-training-")
    training_dataset_path = Path(training_workspace.name)
    registered_student_ids = list(Student.objects.order_by("student_id").values_list("student_id", flat=True))
    included_student_ids = []

    for student_id in registered_student_ids:
        source_folder = dataset_path / student_id
        face_images = sorted(source_folder.glob("face_*.jpg"))[:30] if source_folder.exists() else []
        if len(face_images) < 30:
            continue
        destination_folder = training_dataset_path / student_id
        destination_folder.mkdir(parents=True)
        for image_path in face_images:
            shutil.copy2(image_path, destination_folder / image_path.name)
        included_student_ids.append(student_id)

    if len(included_student_ids) < 2:
        training_workspace.cleanup()
        raise ValueError("At least 2 registered students with 30 captured photos each are required to train the CNN.")

    # -----------------------------
    # Image settings
    # -----------------------------

    image_height = 128
    image_width = 128

    batch_size = 16


    # -----------------------------
    # Load training dataset
    # -----------------------------

    train_dataset = (tf.keras.utils.image_dataset_from_directory(
            training_dataset_path,
            validation_split=0.2,
            subset="training",
            seed=123,
            image_size=(image_height,image_width),
            batch_size=batch_size,
            color_mode="grayscale"
        )
    )

    # -----------------------------
    # Load validation dataset
    # -----------------------------

    validation_dataset = (tf.keras.utils.image_dataset_from_directory(training_dataset_path,
            validation_split=0.2,
            subset="validation",
            seed=123,
            image_size=(image_height,image_width),
            batch_size=batch_size,
            color_mode="grayscale"
        )
    )


    # -----------------------------
    # Class names
    # -----------------------------

    class_names = (train_dataset.class_names)
    number_of_students = len(class_names)

    print("Classes:",class_names)
    print("Number of students:",number_of_students)

    if number_of_students < 2:
        raise ValueError("At least 2 students are required to train the CNN.")


    # -----------------------------
    # CNN
    # -----------------------------

    model = tf.keras.Sequential([

        tf.keras.layers.Input(shape=(128, 128, 1)),

        tf.keras.layers.Rescaling(1.0 / 255),

        tf.keras.layers.Conv2D(32,(3, 3),activation="relu"),

        tf.keras.layers.MaxPooling2D((2, 2)),

        tf.keras.layers.Conv2D(64,(3, 3), activation="relu"),

        tf.keras.layers.MaxPooling2D((2, 2)),

        tf.keras.layers.Conv2D(128,(3, 3),activation="relu"),

        tf.keras.layers.MaxPooling2D((2, 2)),

        tf.keras.layers.Flatten(),

        tf.keras.layers.Dense(128,activation="relu"),

        tf.keras.layers.Dropout( 0.5),
        tf.keras.layers.Dense(number_of_students,activation="softmax")
    ])


    # -----------------------------
    # Compile
    # -----------------------------

    model.compile(optimizer="adam",loss=("sparse_categorical_crossentropy"),metrics=["accuracy"])
    model.summary()

    # -----------------------------
    # Train
    # -----------------------------
    epochs = 15
    print("\nModel training started...", flush=True)
    history = model.fit(
        train_dataset,
        validation_data=validation_dataset,
        epochs=epochs,
        verbose=0,
        callbacks=[TerminalMetricsCallback(epochs)],
    )
    print("\nModel training completed.", flush=True)
    # -----------------------------
    # Save model
    # -----------------------------

    model.save(model_path)

    # -----------------------------
    # Save classes
    # -----------------------------

    with open(classes_path,"w") as file:

        json.dump(class_names,file)

    training_workspace.cleanup()

    print("\nModel saved:",model_path)

    print("Classes saved:",classes_path)

    return { "model_path": str(model_path),
            "classes_path": str(classes_path),
            "class_names": class_names,
            "accuracy": float(history.history["accuracy"][-1]),
            "validation_accuracy": float(history.history["val_accuracy"][-1]),
            }
