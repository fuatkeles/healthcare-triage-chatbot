import { initializeApp } from 'firebase/app';
import { getFirestore } from 'firebase/firestore';
import { getDatabase } from 'firebase/database';
import { getAuth } from 'firebase/auth';

// Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyDMNJG9vnpVid8TjEocSRqCJDGZi4iQEHU",
  authDomain: "chat-bot-a8ae4.firebaseapp.com",
  projectId: "chat-bot-a8ae4",
  storageBucket: "chat-bot-a8ae4.firebasestorage.app",
  messagingSenderId: "1061857060131",
  appId: "1:1061857060131:web:5fe7de79a9d1969ebd5896",
  measurementId: "G-NF2ZBNJXZH"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firestore
export const db = getFirestore(app);

// Initialize Realtime Database
export const realtimeDb = getDatabase(app);

// Initialize Auth
export const auth = getAuth(app);

// Database URL
export const REALTIME_DB_URL = "https://chat-bot-a8ae4-default-rtdb.europe-west1.firebasedatabase.app/";

export default app;