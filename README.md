# DeepGuard — Deepfake Detection Using Frequency-Domain and Transformer Models

**DeepGuard** is a full-stack web application for detecting deepfake videos and images. It combines **frequency-domain signal processing** with a **PyTorch transformer encoder** to classify media as real or fake. All detection processing runs **locally on the server** — no third-party APIs are used.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Technology Stack](#technology-stack)
3. [Key Features](#key-features)
4. [Module & Panel Functionality](#module--panel-functionality)
   - [Public / Landing Module](#public--landing-module)
   - [Authentication Module](#authentication-module)
   - [User Panel](#user-panel)
   - [Admin Panel](#admin-panel)
   - [Detection Module (Backend Pipeline)](#detection-module-backend-pipeline)
5. [Project Structure](#project-structure)
6. [Prerequisites](#prerequisites)
7. [Installation & Setup](#installation--setup)
8. [How to Run the Project](#how-to-run-the-project)
9. [Default Credentials](#default-credentials)
10. [Supported File Formats](#supported-file-formats)
11. [Detection Pipeline Flow](#detection-pipeline-flow)
12. [Database & Seed Data](#database--seed-data)
13. [Configuration](#configuration)
14. [Troubleshooting](#troubleshooting)

---

## Project Overview

DeepGuard provides a professional business-level platform where:

- **Users** upload videos or images and receive detailed deepfake analysis reports.
- **Administrators** manage users, monitor detections, configure ML settings, train models, and view system analytics.
- **The detection engine** extracts frames, performs FFT frequency analysis, and uses a transformer model for real/fake classification.

The system is designed as an educational and demonstration platform for deepfake detection research using frequency-domain and transformer-based approaches.

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Web Framework** | Flask 3.0 | Backend application, routing, request handling |
| **ORM / Database** | Flask-SQLAlchemy, SQLite | Data persistence and models |
| **Authentication** | Flask-Login, Werkzeug | Session management and password hashing |
| **Forms** | Flask-WTF, WTForms | Form validation |
| **Computer Vision** | OpenCV (headless) | Video/image processing, face detection, frame extraction |
| **Numerical Computing** | NumPy, SciPy | FFT, DCT, array operations |
| **Deep Learning** | PyTorch 2.3 | Transformer encoder for classification |
| **Image Processing** | Pillow | Image handling |
| **PDF Reports** | ReportLab | Detection report generation |
| **Frontend** | HTML5, CSS3, JavaScript | Responsive UI with dedicated User & Admin themes |
| **Template Engine** | Jinja2 | Server-side rendering |

---

## Key Features

- Attractive landing page with product overview and awareness content
- Role-based access control (Admin / User)
- Professional admin dashboard with sidebar navigation
- Professional user portal with sidebar navigation
- Video and image deepfake detection
- Frame-level and frequency-domain analysis
- Transformer-based real/fake classification with confidence scores
- Downloadable PDF detection reports
- Admin model training on custom dataset
- Configurable frame extraction, frequency, and transformer settings
- System logs, login history, upload history, detection history
- Daily and monthly activity reports
- User feedback and contact query management
- Seed script with 8 dummy records per entity for testing

---

## Module & Panel Functionality

### Public / Landing Module

| Page | Route | Functionality |
|------|-------|---------------|
| **Landing Page** | `/` | Hero section, feature highlights, statistics, call-to-action |
| **About** | `/about` | Project description and technology overview |
| **Deepfake Awareness** | `/awareness` | Educational content on deepfakes and identification tips |
| **Upload Guidelines** | `/guidelines` | Supported formats, file size limits, best practices |
| **Contact** | `/contact` | Public contact form for inquiries |

---

### Authentication Module

| Feature | Route | Functionality |
|---------|-------|---------------|
| **User Login** | `/auth/login` | Login with username or email; redirects to Admin or User dashboard |
| **User Registration** | `/auth/register` | New user account creation with validation |
| **Logout** | `/auth/logout` | Session termination and redirect to home |

**Security features:**
- Password hashing (Werkzeug)
- Account activation/deactivation (admin-controlled)
- Login history tracking with IP address
- Role-based route protection (`admin_required`, `user_required`)

---

### User Panel

Access: `/user/*` — requires user login

#### Dashboard
| Feature | Route | Description |
|---------|-------|-------------|
| User Dashboard | `/user/dashboard` | Stats (uploads, detections, real/fake counts), recent activity, quick actions, pipeline overview |

#### Account Management
| Feature | Route | Description |
|---------|-------|-------------|
| Manage Profile | `/user/profile` | Update full name, email, phone |
| Change Password | `/user/change-password` | Update account password |

#### Detection Operations
| Feature | Route | Description |
|---------|-------|-------------|
| Upload Video | `/user/upload` | Upload video with title and category; format & size validation |
| Video Preview | `/user/videos/<id>/preview` | Preview uploaded video metadata and thumbnail |
| Submit Detection | `/user/videos/<id>/detect` | Submit video for full deepfake analysis pipeline |
| Image Detection | `/user/detect/image` | Upload single image frame for analysis |
| Detection Result | `/user/results/<id>` | View result, confidence, frame analysis, frequency patterns, summary |
| Download Report | `/user/results/<id>/download` | Download PDF detection report |
| My Videos | `/user/videos` | List all uploaded videos with metadata |
| Detection History | `/user/history` | Search and filter past detections; delete own records |

#### Support & Resources
| Feature | Route | Description |
|---------|-------|-------------|
| Submit Feedback | `/user/feedback` | Send feedback and view feedback status |
| Contact Support | `/user/contact` | Send support queries while logged in |
| Guidelines | `/guidelines` | Upload guidelines (public page) |
| Awareness | `/awareness` | Deepfake awareness information (public page) |

**User detection result details include:**
- Real or Fake classification
- Confidence score (%)
- Frame-level analysis (noise, texture, anomaly flags)
- Frequency pattern analysis (FFT bands, anomaly ratio)
- Final detection summary
- PDF report download

---

### Admin Panel

Access: `/admin/*` — requires admin login

#### Dashboard & Account
| Feature | Route | Description |
|---------|-------|-------------|
| Admin Dashboard | `/admin/dashboard` | System stats, recent detections, system health, recent users, activity logs |
| Admin Profile | `/admin/profile` | Manage administrator profile |
| Change Password | `/admin/change-password` | Update admin password |

#### User & Content Management
| Feature | Route | Description |
|---------|-------|-------------|
| Manage Users | `/admin/users` | View, search, activate/deactivate, delete user accounts |
| View User Details | `/admin/users/<id>` | Full user profile, detection history, uploaded videos |
| Video Categories | `/admin/categories` | List all categories |
| Add Category | `/admin/categories/add` | Create new video category |
| Edit Category | `/admin/categories/<id>/edit` | Update category name and description |
| Delete Category | `/admin/categories/<id>/delete` | Remove category |
| Uploaded Videos | `/admin/videos` | View all user-uploaded videos |
| Video Details | `/admin/videos/<id>` | Full video metadata and owner info |
| Delete Video | `/admin/videos/<id>/delete` | Remove inappropriate uploaded videos |

#### Detection Management
| Feature | Route | Description |
|---------|-------|-------------|
| All Detection Requests | `/admin/detections` | View all requests with status filters |
| Pending Requests | `/admin/detections?status=pending` | View pending detection requests |
| Completed Requests | `/admin/detections?status=completed` | View completed detections |
| Failed Requests | `/admin/detections?status=failed` | View failed detections |
| Detection Detail | `/admin/detections/<id>` | Full report with frame & frequency analysis |
| Detection Results | `/admin/detection/results` | Filter real/fake completed results |
| Download Report | `/admin/detections/<id>/report` | Download PDF report |

#### ML & Dataset Management
| Feature | Route | Description |
|---------|-------|-------------|
| Dataset Records | `/admin/dataset` | View real/fake training samples |
| Upload Dataset | `/admin/dataset/upload` | Upload real or fake video/image samples |
| Delete Dataset Record | `/admin/dataset/<id>/delete` | Remove dataset entry |
| Frame Extraction Settings | `/admin/settings/frames` | Configure frame count, size, face detection |
| Frequency Settings | `/admin/settings/frequency` | Configure FFT bands, noise threshold, texture sensitivity |
| Transformer Settings | `/admin/settings/transformer` | Configure layers, heads, embedding dimension, dropout |
| Model Training Status | `/admin/model` | View training progress, accuracy, loss |
| Train Model | `/admin/model/train` | Start model training on dataset |
| Update Model | `/admin/model/update` | Reload detection model from disk |
| Test Model | `/admin/model/test` | Test model with a sample video |

#### Communication
| Feature | Route | Description |
|---------|-------|-------------|
| User Feedback | `/admin/feedback` | View feedback, update status, delete entries |
| Contact Queries | `/admin/contacts` | View messages, manage reply status, delete |

#### Reports & Logs
| Feature | Route | Description |
|---------|-------|-------------|
| System Logs | `/admin/logs` | View all system audit logs |
| Login History | `/admin/login-history` | Track login attempts with IP and status |
| Upload History | `/admin/upload-history` | Record of all file uploads |
| Detection History | `/admin/detection-history` | Historical detection operation log |
| Daily Report | `/admin/reports/daily` | Today's activity summary |
| Monthly Report | `/admin/reports/monthly` | Monthly platform metrics and analytics |

---

### Detection Module (Backend Pipeline)

The detection engine runs entirely inside the application — no external API calls.

| Step | Component | File | Description |
|------|-----------|------|-------------|
| 1 | Video Upload | `video_processor.py` | Accept and store uploaded media |
| 2 | Format Checking | `video_processor.py` | Validate MP4, AVI, MOV, MKV, WEBM |
| 3 | Size Checking | `video_processor.py` | Enforce 100 MB maximum file size |
| 4 | Frame Extraction | `video_processor.py` | Sample frames evenly from video |
| 5 | Face Region Detection | `video_processor.py` | Haar cascade face crop (optional) |
| 6 | Frequency-Domain Conversion | `frequency_analysis.py` | 2D FFT magnitude spectrum |
| 7 | Noise Pattern Analysis | `frequency_analysis.py` | Laplacian + DCT high-frequency energy |
| 8 | Texture Irregularity Analysis | `frequency_analysis.py` | Sobel gradient texture scoring |
| 9 | Frame Feature Extraction | `frequency_analysis.py` | Per-frame band energy and scores |
| 10 | Transformer Feature Learning | `transformer_model.py` | Multi-head attention encoder |
| 11 | Real/Fake Classification | `transformer_model.py` | Softmax classification with probabilities |
| 12 | Confidence Score Calculation | `transformer_model.py` | Percentage confidence output |
| 13 | Result Storage | `detection_service.py` | Save results to database |
| 14 | Result Display | User/Admin templates | Render analysis in portal |
| 15 | Report Generation | `detection_service.py` | Generate downloadable PDF via ReportLab |

**Service files:**
```
app/services/
├── video_processor.py      # Video/image validation, frame extraction, face detection
├── frequency_analysis.py   # FFT, noise, texture, band energy analysis
├── transformer_model.py    # PyTorch transformer classifier and training
└── detection_service.py    # Orchestrates pipeline and PDF report generation
```

---

## Project Structure

```
Deepfake Detection Using Frequency-Domain and Transformer Models/
│
├── app/
│   ├── __init__.py                 # Flask app factory
│   ├── models.py                   # SQLAlchemy database models (14 tables)
│   │
│   ├── routes/
│   │   ├── auth.py                 # Login, register, logout
│   │   ├── main.py                 # Landing, about, awareness, guidelines, contact
│   │   ├── user.py                 # User panel routes
│   │   ├── admin.py                # Admin panel routes
│   │   └── detection.py            # File serving (uploads, thumbnails)
│   │
│   ├── services/
│   │   ├── video_processor.py      # Video/image processing
│   │   ├── frequency_analysis.py   # Frequency-domain analysis
│   │   ├── transformer_model.py    # Transformer ML model
│   │   └── detection_service.py    # Detection orchestration & reports
│   │
│   ├── utils/
│   │   ├── helpers.py              # Settings, logging, file utilities
│   │   └── decorators.py           # admin_required, user_required
│   │
│   ├── templates/
│   │   ├── landing.html            # Public pages
│   │   ├── auth/                   # Login & register
│   │   ├── user/                   # User panel (11 pages)
│   │   └── admin/                  # Admin panel (26 pages)
│   │
│   └── static/
│       ├── css/
│       │   ├── style.css           # Global styles
│       │   ├── user.css            # User panel theme
│       │   └── admin.css           # Admin panel theme
│       └── js/
│           ├── main.js
│           ├── user.js
│           └── admin.js
│
├── uploads/                        # User uploaded videos & images
├── dataset/                        # ML training dataset (real/ & fake/)
├── models/                         # Trained transformer model weights
├── reports/                        # Generated PDF detection reports
│
├── config.py                       # Application configuration
├── seed.py                         # Database seeder (dummy data)
├── run.py                          # Application entry point
├── requirements.txt                # Python dependencies
└── README.md                       # Project documentation
```

---

## Prerequisites

- **Python** 3.10 or higher (3.12 recommended)
- **pip** (Python package manager)
- **Git** (optional, for cloning)
- **4 GB+ RAM** recommended (PyTorch model loading)
- **Windows / Linux / macOS**

---

## Installation & Setup

### Step 1 — Navigate to project directory

```powershell
cd "c:\Project\Python Source Code\Deepfake Detection Using Frequency-Domain and Transformer Models"
```

### Step 2 — Create virtual environment

**Windows:**
```powershell
python -m venv venv
venv\Scripts\activate
```

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** Installing PyTorch may take several minutes depending on your internet speed.

### Step 4 — Seed the database

```bash
python seed.py
```

This creates:
- 1 admin account
- 8 user accounts
- 8 video categories
- 8 videos with detection records
- 8 dataset samples
- 8 feedback entries
- 8 contact queries
- System logs, login history, and model training record

### Step 5 — Run the application

```bash
python run.py
```

---

## How to Run the Project

1. Activate the virtual environment (see above)
2. Run `python run.py`
3. Open your browser and go to:

   **http://localhost:5000**

4. Use the credentials below to log in

### Application URLs

| Page | URL |
|------|-----|
| Home / Landing | http://localhost:5000/ |
| Login | http://localhost:5000/auth/login |
| Register | http://localhost:5000/auth/register |
| User Dashboard | http://localhost:5000/user/dashboard |
| Admin Dashboard | http://localhost:5000/admin/dashboard |

### Typical User Workflow

1. Register or login as a user
2. Go to **Upload Video** or **Image Detection**
3. Upload a supported file
4. Submit for detection analysis
5. View results with confidence score and frame analysis
6. Download PDF report from the results page

### Typical Admin Workflow

1. Login as admin
2. Review dashboard statistics
3. Manage users, videos, and detection requests
4. Upload real/fake samples to the dataset
5. Configure frame, frequency, and transformer settings
6. Train and test the detection model
7. Review logs and generate daily/monthly reports

---

## Default Credentials

### Administrator

| Field | Value |
|-------|-------|
| **Username** | `admin` |
| **Email** | `admin@deepguard.com` |
| **Password** | `admin123` |
| **Dashboard** | http://localhost:5000/admin/dashboard |

### Standard Users (all passwords: `user123`)

| Username | Email | Full Name | Status |
|----------|-------|-----------|--------|
| `john_doe` | john@email.com | John Doe | Active |
| `jane_smith` | jane@email.com | Jane Smith | Active |
| `mike_wilson` | mike@email.com | Mike Wilson | Active |
| `sarah_jones` | sarah@email.com | Sarah Jones | Active |
| `david_brown` | david@email.com | David Brown | Active |
| `emily_davis` | emily@email.com | Emily Davis | Active |
| `chris_miller` | chris@email.com | Chris Miller | **Inactive** |
| `lisa_taylor` | lisa@email.com | Lisa Taylor | Active |

> **Recommended test login:** `john_doe` / `user123`

---

## Supported File Formats

### Video (max 100 MB)

| Format | Extension |
|--------|-------------|
| MP4 | `.mp4` |
| AVI | `.avi` |
| MOV | `.mov` |
| MKV | `.mkv` |
| WEBM | `.webm` |

### Image

| Format | Extension |
|--------|-------------|
| JPEG | `.jpg`, `.jpeg` |
| PNG | `.png` |
| BMP | `.bmp` |
| WEBP | `.webp` |

---

## Detection Pipeline Flow

```
Upload Video/Image
        │
        ▼
  Format & Size Validation
        │
        ▼
  Frame Extraction (with optional Face Detection)
        │
        ▼
  Frequency-Domain Analysis (2D FFT)
        │
        ├── Noise Pattern Analysis (Laplacian + DCT)
        └── Texture Irregularity Analysis (Sobel)
        │
        ▼
  Transformer Encoder Classification
        │
        ▼
  Real / Fake Result + Confidence Score
        │
        ├── Store in Database
        ├── Display in Portal
        └── Generate PDF Report
```

---

## Database & Seed Data

The application uses **SQLite** (`deepfake_detection.db` in the project root).

### Database Models

| Model | Purpose |
|-------|---------|
| `User` | Admin and user accounts |
| `VideoCategory` | Video classification categories |
| `Video` | Uploaded video records |
| `DetectionRequest` | Detection jobs and results |
| `DatasetRecord` | ML training dataset entries |
| `SystemSetting` | Frame, frequency, transformer config |
| `ModelTraining` | Model training runs and metrics |
| `Feedback` | User feedback submissions |
| `ContactQuery` | Contact form messages |
| `SystemLog` | System audit logs |
| `LoginHistory` | Login attempt records |
| `UploadHistory` | File upload records |
| `DetectionHistory` | Detection operation history |

### Reset & Re-seed Database

```bash
python seed.py
```

> **Warning:** This drops and recreates all tables, removing existing data.

---

## Configuration

Configuration is defined in `config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `MAX_CONTENT_LENGTH` | 100 MB | Maximum upload file size |
| `DEFAULT_FRAME_COUNT` | 16 | Frames extracted per video |
| `DEFAULT_FRAME_SIZE` | 224 px | Frame resize dimension |
| `DEFAULT_FFT_BANDS` | 8 | Frequency bands for FFT analysis |
| `DEFAULT_TRANSFORMER_LAYERS` | 4 | Transformer encoder layers |
| `DEFAULT_TRANSFORMER_HEADS` | 4 | Attention heads |
| `DEFAULT_EMBED_DIM` | 128 | Embedding dimension |

Admin can modify frame, frequency, and transformer settings from the admin panel without editing code.

---

## Troubleshooting

### Port already in use
Change the port in `run.py`:
```python
app.run(debug=True, host="0.0.0.0", port=5001)
```

### Detection fails with OpenCV error
Ensure you are using the latest `frequency_analysis.py` (NumPy-based band masks, uint8 for OpenCV filters). Restart the app after code updates.

### PyTorch install is slow or fails
Install CPU-only PyTorch separately:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

### Database errors after code changes
Re-run the seed script:
```bash
python seed.py
```

### Model training requires minimum samples
Upload at least **4 dataset samples** (mix of real and fake) before training from **Admin → Model Training**.

---

## Important Note

This project does **not** use any third-party API. All deepfake detection processing — including frame extraction, frequency-domain analysis, transformer classification, and report generation — is handled entirely within the local system.

---

## License

Educational project — **Deepfake Detection Using Frequency-Domain and Transformer Models**.
Licensed under the MIT License.
