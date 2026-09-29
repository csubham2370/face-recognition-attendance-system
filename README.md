# Face Recognition Attendance System

A Django-based attendance management system that uses a convolutional neural network (CNN) to identify registered students from a camera image and record their attendance.

The project includes an administrator dashboard, student and administrator management, browser-based face capture, model training, live recognition, attendance controls, REST API endpoints, and email-based password reset.

## Features

- Register, view, edit, and delete students
- Capture student face images with a webcam
- Train a TensorFlow/Keras CNN from captured images
- Recognize students and record attendance automatically
- Prevent duplicate attendance records for the same student and date
- Open or close attendance submission from the admin dashboard
- View attendance details, status, time, and prediction confidence
- Manage custom administrator accounts
- Reset administrator passwords by email
- Access paginated student and administrator REST APIs
- Use Django management commands for training and live recognition

## Tech Stack

- **Backend:** Django 6, Django REST Framework
- **Database:** PostgreSQL
- **Machine learning:** TensorFlow, Keras, NumPy, scikit-learn
- **Computer vision:** OpenCV
- **Authentication:** Custom admin accounts, sessions, and JWT utilities
- **Frontend:** Django templates and JavaScript
- **Email:** SMTP (configured for Gmail by default)

## Project Structure

```text
.
├── attendance/                  # Main Django application
│   ├── management/commands/     # Model training and recognition commands
│   ├── migrations/              # Database migrations
│   ├── ml/                      # CNN training and prediction code
│   ├── static/attendance/js/    # Frontend JavaScript
│   ├── templates/attendance/    # Django templates
│   ├── api_views.py             # REST API views
│   ├── models.py                # Student, attendance, admin, and control models
│   ├── urls.py                  # Application routes
│   └── views.py                 # Web views and recognition workflow
├── attendance_project/          # Django project configuration
├── dataset/                     # Captured training images grouped by student ID
├── media/student_photos/        # Uploaded student profile photos
├── ml_models/                   # Trained Keras model and class-name mapping
├── manage.py
└── requirements.txt
```

## Prerequisites

- Python 3.11 or newer
- PostgreSQL
- A webcam or camera-enabled device
- A virtual environment (recommended)

TensorFlow and OpenCV are large dependencies, so installation may take several minutes.

## Installation

1. Clone the repository and enter the project directory:

   ```bash
   git clone <your-repository-url>
   cd <repository-folder>
   ```

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   On Windows PowerShell:

   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. Install the dependencies:

   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Create a PostgreSQL database and user, then grant the user access to the database.

5. Create a `.env` file in the project root:

   ```env
   DB_NAME=face_attendance
   DB_USER=postgres
   DB_PASSWORD=your_database_password
   DB_HOST=localhost
   DB_PORT=5432

   DJANGO_SECRET_KEY=replace_with_a_long_random_secret
   JWT_SECRET_KEY=replace_with_another_long_random_secret

   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your_email@gmail.com
   EMAIL_HOST_PASSWORD=your_gmail_app_password
   DEFAULT_FROM_EMAIL=your_email@gmail.com
   ```

   Generate secure keys, for example:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(50))"
   ```

   If you use Gmail password reset, create a Google App Password instead of placing your normal account password in `.env`.

6. Apply the database migrations:

   ```bash
   python manage.py migrate
   ```

7. Create an initial administrator. You can first create a Django superuser for `/admin/`:

   ```bash
   python manage.py createsuperuser
   ```

   The application also has its own `AdminUser` accounts, which can be created from the application's admin management page after signing in with an existing application administrator. For a fresh database, an initial `AdminUser` may be added through the Django admin site.

8. Start the development server:

   ```bash
   python manage.py runserver
   ```

9. Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in a browser.

## Usage Workflow

1. Sign in to the application admin panel.
2. Register at least two students.
3. Open each student's capture page and collect 30 face images.
4. Train the model from the dashboard or run:

   ```bash
   python manage.py train_faces
   ```

5. Open attendance from the dashboard.
6. Go to the student recognition page, allow camera access, and scan a face.
7. Review the recorded attendance on the dashboard or student detail page.

The training process only includes students who still exist in the database and have at least 30 captured images. At least two eligible students are required. The resulting files are saved as:

```text
ml_models/face_recognition_model.keras
ml_models/class_names.json
```

Recognition currently accepts predictions with at least **80% confidence**.

## Management Commands

Train the CNN model:

```bash
python manage.py train_faces
```

Run desktop live face recognition using OpenCV:

```bash
python manage.py recognize_faces
```

## Main Routes

| Route | Purpose |
|---|---|
| `/` | Application admin login |
| `/dashboard/` | Attendance dashboard |
| `/students/` | Student list |
| `/students/register/` | Register a student |
| `/recognition/` | Administrator recognition page |
| `/student/recognition/` | Student attendance recognition page |
| `/admin-panel/users/` | Application administrator management |
| `/admin-panel/forgot-password/` | Password reset request |
| `/admin/` | Built-in Django admin site |

## REST API

The project provides these endpoints:

| Method | Endpoint | Description |
|---|---|---|
| `GET`, `POST` | `/api/students/` | List or create students |
| `GET`, `PUT`, `PATCH`, `DELETE` | `/api/students/<id>/` | Manage one student |
| `GET`, `POST` | `/api/admins/` | List or create application admins |
| `GET`, `PUT`, `PATCH`, `DELETE` | `/api/admins/<id>/` | Manage one application admin |

These API views use the application's active administrator authentication and permissions.

## Data and Security Notes

- Never commit `.env`, database passwords, email credentials, or secret keys.
- Face images and trained models contain sensitive biometric information. Do not publish real user data in a public repository.
- Keep `dataset/`, `media/`, and `ml_models/` private or replace their contents with safe sample data before publishing.
- The current settings enable `DEBUG` and leave `ALLOWED_HOSTS` empty. Configure both appropriately before deployment.
- Use HTTPS and secure cookies in production, and run Django's deployment check:

  ```bash
  python manage.py check --deploy
  ```

## Troubleshooting

### Database connection errors

Confirm that PostgreSQL is running and that all `DB_*` values in `.env` match the database and user you created.

### Camera does not open

Grant camera permission to the browser or terminal. Browser camera access generally requires `localhost` or HTTPS.

### Training reports too few students

Register at least two students and capture exactly 30 usable images for each student before training.

### Model and student data are out of sync

Retrain the model after adding or removing students. This refreshes both the Keras model and `class_names.json`.

### Password reset email is not delivered

Check the SMTP settings and use a Gmail App Password when Gmail is the email provider.

## License

No license has been specified. Add a `LICENSE` file before distributing or accepting contributions to the project.
