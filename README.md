<div align="center">

# 🏋️ FitTrack: Modern Gym & Fitness Management PWA

**Production-Ready, Offline-First Progressive Web App (PWA) for Gym Owners & Fitness Enthusiasts**

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0+-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![PWA](https://img.shields.io/badge/PWA-Ready-5A0FC8?style=for-the-badge&logo=pwa&logoColor=white)](https://web.dev/progressive-web-apps/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

<br/>

[![Live Production VPS](https://img.shields.io/badge/🌐_Live_App-gym.137.23.47.199.sslip.io-00C853?style=for-the-badge&logo=google-chrome&logoColor=white)](https://gym.137.23.47.199.sslip.io)
[![GitHub Pages Demo](https://img.shields.io/badge/📱_GitHub_Pages-Interactive_Demo-38BDF8?style=for-the-badge&logo=github&logoColor=white)](https://themusafirr.github.io/fittrack-fitness-pwa/)
[![Telegram Support](https://img.shields.io/badge/💬_Telegram-@the__musafir-0088cc?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/the_musafir)

<br/>

[⭐ Star This Repo](https://github.com/themusafirr/fittrack-fitness-pwa) • [🌐 Live App](https://gym.137.23.47.199.sslip.io) • [📱 GitHub Demo](https://themusafirr.github.io/fittrack-fitness-pwa/) • [💬 Contact Developer](https://t.me/the_musafir)

<br/><br/>

<img src="./assets/preview.png" width="100%" alt="FitTrack Fitness Platform Live UI Preview" style="border-radius: 14px; border: 1px solid rgba(255, 255, 255, 0.15); box-shadow: 0 10px 35px rgba(0, 0, 0, 0.6);" />

</div>

---

## ⚡ Overview

**FitTrack** is a high-performance, full-stack Fitness & Gym Management Platform designed to run seamlessly on both desktop browsers and mobile devices as an installable **Progressive Web App (PWA)**.

Built with **Python (Flask)** and **SQLite**, it features offline support via a custom Service Worker, member registration, automated body metrics calculation (BMI & Calorie targets), workout logging, and real-time subscription management.

---

## ✨ Key Features

- 📱 **Progressive Web App (PWA):** Installable on Android, iOS, and Desktop with offline caching via `sw.js` and `manifest.json`.
- 🔐 **Secure Authentication:** User registration, password hashing (Werkzeug), and session protection.
- 📊 **Member & Health Analytics:** Automatic calculation of BMI, BMR, daily caloric expenditure, and workout progress over time.
- 🏋️ **Workout & Routine Tracker:** Customizable workout splits (Push/Pull/Legs, Upper/Lower, Full Body) with set and rep tracking.
- 💳 **Membership & Plan Management:** Built-in membership tiers, validity tracking, and renewal reminders.
- 🎨 **Responsive Dark/Light UI:** Clean, modern gym dashboard crafted with responsive CSS3.

---

## 🏗️ Architecture

```text
├── app.py              # Flask core routing & business logic
├── fitness.db          # SQLite database (auto-initialized on first run)
├── static/
│   ├── manifest.json   # PWA manifest metadata
│   ├── sw.js           # Service Worker for offline asset caching
│   └── ...             # Banners, icons, and UI assets
└── templates/
    ├── index.html      # Marketing & landing page
    ├── login.html      # Authentication portal
    ├── register.html   # Onboarding registration
    └── dashboard.html  # Interactive workout & membership dashboard
```

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/themusafirr/fittrack-fitness-pwa.git
cd fittrack-fitness-pwa
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Application
```bash
python3 app.py
```
Open your browser and navigate to `http://127.0.0.1:5000`.

---

## 👨‍💻 Author

**Pankaj Kalosiya (@themusafirr)**  
- 💼 Portfolio: [github.com/themusafirr](https://github.com/themusafirr)  
- 💬 Telegram: [@the_musafir](https://t.me/the_musafir)  
- 📸 Instagram: [@the.musafirrr__](https://instagram.com/the.musafirrr__)  

---

## ⭐️ Show Your Support

If this project helped your gym or fitness workflow, please give it a **Star ⭐**!
