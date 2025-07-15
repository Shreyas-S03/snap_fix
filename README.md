# Snap_Fix

Snap_Fix is a modern, AI-powered civic issue reporting platform built with Flask. It enables citizens to report local issues (like potholes, garbage, broken streetlights) with images and location data, and provides an admin dashboard for efficient management and resolution.

---

## 🚀 Features

- **User Authentication:** Secure signup/login for users and admins.
- **Issue Reporting:** Users can report issues with descriptions, images, and precise locations (via map).
- **AI-Powered Suggestions:** Google Vision API analyzes uploaded images to auto-suggest issue category and priority.
- **Image Quality Feedback:** Users receive instant feedback on image quality.
- **Admin Dashboard:** View, filter, and update status of all reported issues.
- **Map View:** Visualize issues on a map with category and priority info.
- **Modern UI/UX:** Bootstrap 5, glassmorphism, dark mode toggle, Google Fonts, SweetAlert2 toasts.
- **Accessibility:** ARIA labels, keyboard navigation, color contrast improvements.
- **Security:** All secrets managed via environment variables; no sensitive data in code.
- **PostgreSQL Backend:** Easy deployment on platforms like Render.

---


## 🛠️ Tech Stack

- **Backend:** Python, Flask, Flask-Login, psycopg2 (PostgreSQL)
- **Frontend:** Bootstrap 5, JavaScript, Google Maps API
- **AI Integration:** Google Cloud Vision API
- **Deployment:** Render (compatible), Gunicorn

---

## ⚙️ Setup & Installation

### 1. **Clone the repository**
```sh
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
```

### 2. **Create and configure your environment variables**

- Copy `.env.example` to `.env` and fill in your secrets:
  ```
  cp .env.example .env
  ```
- Add your PostgreSQL credentials, Flask secret key, Google Maps API key, and Google Vision API credentials.

### 3. **Install dependencies**
```sh
pip install -r requirements.txt
```

### 4. **Set up the database**
- Create a PostgreSQL database and run the schema (see your schema file or migration instructions).

### 5. **Run the app locally**
```sh
python app1.py
```
- The app will be available at `http://127.0.0.1:5000/`

---

## 🗝️ Environment Variables

- See `.env.example` for all required variables.
- **Never commit your real `.env` or service account files.**

---


🔑 Google Cloud CLI Setup & Vision API Authentication

To use the Google Vision API client library, you need to authenticate your local environment with Google Cloud. Follow these steps:

### 1. **Install the Google Cloud CLI**

- Download and install the Google Cloud CLI from the [official documentation](https://cloud.google.com/sdk/docs/install).

### 2. **Initialize and Authenticate**

Open a terminal and run:

```sh
gcloud init
```
- Follow the prompts to log in with your Google account and select your project.

### 3. **Enable the Vision API**

If you haven’t already, enable the Vision API for your project:

```sh
gcloud services enable vision.googleapis.com
```

---


## 📝 Deployment

- Ready for deployment on Render or similar platforms.
- Use `Procfile` and set environment variables in your deployment dashboard.
- Ensure `static/uploads/` is created on the server (the app will auto-create it if missing).

---

## 📁 Project Structure
<pre>
<code>
Snap_Fix/
├── app1.py
├── requirements.txt
├── Procfile
├── .env.example
├── static/
│ └── uploads/ # User-uploaded images (gitignored)
├── templates/
│ ├── admin_dashboard.html
│ ├── index.html
│ ├── login.html
│ ├── signup.html
│ ├── user_dashboard.html
│ └── view_map.html
</code>
</pre>


---

## 🙋‍♂️ Contributing

Pull requests and suggestions are welcome! For major changes, please open an issue first to discuss what you would like to change.

---

## 📣 Credits

- [Bootstrap](https://getbootstrap.com/)
- [Google Cloud Vision API](https://cloud.google.com/vision)
- [Flask](https://flask.palletsprojects.com/)
- [SweetAlert2](https://sweetalert2.github.io/)

---

## ✨ Future Ideas

- Push notifications for status updates
- Analytics dashboard for admins
- User profiles and history
- Advanced AI features (object detection, severity estimation)
- PWA/mobile support
