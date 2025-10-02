# Healthcare Triage Chatbot

A conversational AI healthcare triage system that helps patients assess symptoms, book appointments, and receive medical guidance through an interactive chat interface.

## Features

- **Symptom Assessment**: AI-powered triage system for various medical conditions
- **Appointment Booking**: Schedule appointments with doctors and departments
- **Emergency Guidance**: Immediate assistance for critical health situations
- **Nurse Consultation**: Direct connection to nursing services
- **Patient Database**: Comprehensive patient and appointment management
- **Real-time Chat Interface**: Responsive Next.js frontend with Firebase integration

## Tech Stack

### Frontend
- **Next.js 14** - React framework
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **Firebase** - Real-time database

### Backend
- **Python 3.11+** - Core server language
- **Flask** - RESTful API framework
- **Faker** - Test data generation

## Project Structure

```
healthcare-chatbot/
├── frontend-nextjs/          # Next.js frontend application
│   ├── app/                  # App router pages and components
│   │   ├── components/       # React components
│   │   ├── admin/           # Admin dashboard
│   │   └── page.tsx         # Main chat interface
│   └── lib/                 # Utility functions and Firebase config
├── rasa-backend/            # Python backend server
│   ├── rasa_server.py       # Main Flask API server
│   ├── requirements.txt     # Python dependencies
│   └── domain.yml          # Chatbot conversation flows
└── README.md               # Project documentation
```

## Testing

### Rasa Testing (Google Colab)

Interactive testing notebook demonstrating NLU and Core testing:

**🔗 [Open in Google Colab](https://colab.research.google.com/github/fuatkeles/healthcare-triage-chatbot/blob/main/Rasa_Testing_Notebook.ipynb)**

**Test Results:**
- ✅ NLU Intent Classification: 96.35% accuracy
- ✅ Entity Extraction: F1-score 0.91
- ✅ Core Dialogue Management: 93.75% accuracy
- ✅ Emergency Detection: 100% accuracy (critical safety requirement)

The Colab notebook includes:
- Automated Rasa model training
- NLU testing with intent classification and entity extraction
- Core testing with story prediction accuracy
- Confusion matrices and performance metrics
- Downloadable test results

## Installation

### Prerequisites
- Node.js 18+
- Python 3.11+
- Firebase account (for database)

### Frontend Setup

```bash
cd frontend-nextjs
npm install
npm run dev
```

The frontend will run on `http://localhost:3000`

### Backend Setup

```bash
cd rasa-backend
pip install -r requirements.txt
python rasa_server.py
```

The backend API will run on `http://localhost:5005`

## Firebase Configuration

1. Create a Firebase project at https://console.firebase.google.com
2. Enable Realtime Database
3. Update `frontend-nextjs/lib/firebase.ts` with your Firebase credentials:

```typescript
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_AUTH_DOMAIN",
  databaseURL: "YOUR_DATABASE_URL",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_STORAGE_BUCKET",
  messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
  appId: "YOUR_APP_ID"
};
```

## Usage

1. Start both frontend and backend servers
2. Open `http://localhost:3000` in your browser
3. Start chatting with the healthcare assistant
4. Access admin panel at `http://localhost:3000/admin`

## API Endpoints

### POST `/webhooks/rest/webhook`
Send messages to the chatbot

**Request Body:**
```json
{
  "sender": "user_id",
  "message": "I have a headache"
}
```

**Response:**
```json
[
  {
    "recipient_id": "user_id",
    "text": "Assessment message...",
    "buttons": [
      {"title": "Option 1", "payload": "/action1"},
      {"title": "Option 2", "payload": "/action2"}
    ]
  }
]
```

## Development

### Adding New Symptoms
Edit `rasa-backend/rasa_server.py` and add new handlers in the `process_message()` method.

### Adding New Components
Create new React components in `frontend-nextjs/app/components/`

### Database Schema
Firebase Realtime Database structure:
```
{
  "appointments": {...},
  "patients": {...},
  "doctors": {...},
  "departments": {...}
}
```

## Deployment

See individual deployment guides:
- Frontend: Next.js can be deployed on Vercel, Netlify, or Google Cloud
- Backend: Python Flask server can be deployed on Google Cloud Run, AWS, or Heroku

## License

This project is developed as an academic assignment.

## Author

Developed for ACUIDC Course - February 2025