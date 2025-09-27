✋ hand-mcq-rtc

Real-time hand-gesture–based automatic proctoring for online multiple-choice exams
A WebRTC web app that detects and classifies hand gestures through real-time video processing to control MCQ answers and monitor cheating attempts.

🚀 Features

- Gesture-driven interaction: Students answer or undo answers using predefined hand gestures—no keyboard or mouse required.
- Automatic proctoring: Ensures both hands stay visible and flags suspicious activity.
- Real-time video processing: Uses MediaPipe and a custom CNN model for hand-landmark detection and gesture classification.
- Cross-platform: Works entirely in the browser with WebRTC, needing only a standard webcam.

🛠️ Tech Stack

- Frontend: React (WebRTC, WebSocket signaling)
- Backend: Django channels, aiortc, Django + Daphne (ASGI)
- Real-time Media: WebRTC with Google STUN servers (TURN recommended for production)
- ML / CV: MediaPipe, custom CNN trained on hand-landmark angle features

⚙️ Setup & Installation

Prerequisites:
Python 3.11+
Node.js 20+
Ngrok (for local HTTPS/WebRTC testing)

Backend:
pip install -r requirements.txt
# run ASGI server with Daphne
daphne -p 8000 test_rtc.asgi:application

If testing over the internet, expose with:
ngrok http --url=(your ngrok url) 8000

Frontend:
npm install
npm start

Environment for production or separate network testing:
STUN server: stun:stun.l.google.com:19302 (default)
TURN server: set TURN_URL, TURN_USERNAME, TURN_CREDENTIAL in production.

▶️ Usage

Start backend and frontend as above.
Open the frontend URL or localhost.
Allow camera access and begin the MCQ session.

📸 Demo

video