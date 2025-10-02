#!/usr/bin/env python3
"""
Healthcare Chatbot Rasa-Compatible Server
Implements Rasa REST API endpoints for healthcare triage system
Compatible with Rasa Open Source 3.6.0 API
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import datetime
import re
import requests

# Firebase Realtime Database URL
FIREBASE_URL = "https://chat-bot-a8ae4-default-rtdb.europe-west1.firebasedatabase.app"

app = Flask(__name__)
CORS(app, origins="*")

# Triage knowledge base
EMERGENCY_KEYWORDS = [
    "can't breathe", "cant breathe", "cannot breathe", "difficulty breathing",
    "chest pain", "heart attack", "stroke", "unconscious",
    "severe bleeding", "seizure", "choking"
]

URGENT_KEYWORDS = [
    "severe pain", "high fever", "persistent vomiting",
    "deep cut", "broken bone", "severe headache", "severe burn",
    "blood in stool", "blood in urine"
]

GP_KEYWORDS = [
    "fever", "headache", "cough", "stomach pain",
    "sore throat", "ear pain", "back pain", "joint pain",
    "fatigue", "dizziness", "nausea", "rash"
]

class HealthcareBot:
    def __init__(self):
        self.appointments = {}
        self.user_states = {}  # Track conversation state per user
        self.temp_data = {}  # Store partial appointment data

        # Department to doctor mapping (2 per department)
        self.department_doctors = {
            'Cardiology': ['Dr. Sarah Johnson', 'Dr. Robert Williams'],
            'Neurology': ['Dr. Michael Chen', 'Dr. Lisa Anderson'],
            'General Medicine': ['Dr. Emily Rodriguez', 'Dr. David Martinez'],
            'Orthopedics': ['Dr. James Wilson', 'Dr. Patricia Brown'],
            'Pediatrics': ['Dr. Maria Garcia', 'Dr. Christopher Lee'],
            'Emergency': ['Dr. Thomas Anderson', 'Dr. Jennifer Taylor']
        }

        # Symptom to department mapping
        self.symptom_to_department = {
            'chest pain': 'Cardiology',
            'heart': 'Cardiology',
            'palpitations': 'Cardiology',
            'cardiovascular': 'Cardiology',
            'headache': 'Neurology',
            'migraine': 'Neurology',
            'dizziness': 'Neurology',
            'seizure': 'Neurology',
            'stroke': 'Neurology',
            'brain': 'Neurology',
            'numbness': 'Neurology',
            'bone': 'Orthopedics',
            'joint': 'Orthopedics',
            'fracture': 'Orthopedics',
            'sprain': 'Orthopedics',
            'knee pain': 'Orthopedics',
            'back pain': 'Orthopedics',
            'arthritis': 'Orthopedics',
            'child': 'Pediatrics',
            'baby': 'Pediatrics',
            'infant': 'Pediatrics',
            'pediatric': 'Pediatrics',
            'severe bleeding': 'Emergency',
            'unconscious': 'Emergency',
            'can\'t breathe': 'Emergency',
            'difficulty breathing': 'Emergency',
            'severe allergic reaction': 'Emergency',
            'choking': 'Emergency',
        }

    def get_user_state(self, sender_id):
        """Get current state for user"""
        return self.user_states.get(sender_id, None)

    def set_user_state(self, sender_id, state):
        """Set state for user"""
        self.user_states[sender_id] = state

    def get_temp_data(self, sender_id):
        """Get temporary data for user"""
        if sender_id not in self.temp_data:
            self.temp_data[sender_id] = {}
        return self.temp_data[sender_id]

    def clear_temp_data(self, sender_id):
        """Clear temporary data for user"""
        if sender_id in self.temp_data:
            del self.temp_data[sender_id]
        if sender_id in self.user_states:
            del self.user_states[sender_id]

    def auto_assign_department(self, message_lower):
        """Auto-assign department based on symptoms"""
        for keyword, department in self.symptom_to_department.items():
            if keyword in message_lower:
                return department
        return None

    def confirm_appointment(self, sender_id, temp_data):
        """Confirm appointment with all collected information"""
        confirmation = f"HC{random.randint(10000, 99999)}"

        # Get department and select doctor
        department = temp_data.get('department', 'General Medicine')
        available_doctors = self.department_doctors.get(department, ['Dr. Emily Rodriguez'])
        selected_doctor = random.choice(available_doctors)

        # Get appointment date and time from temp_data
        date = temp_data.get('date', 'Tomorrow')
        time = temp_data.get('time', '9:00 AM')

        # Store appointment locally
        if sender_id not in self.appointments:
            self.appointments[sender_id] = []

        appointment_data = {
            "id": confirmation,
            "date": date,
            "time": time,
            "doctor": selected_doctor,
            "department": department,
            "patient_name": temp_data.get('patient_name', ''),
            "patient_surname": temp_data.get('patient_surname', ''),
            "patient_phone": temp_data.get('patient_phone', ''),
            "status": "confirmed",
            "created_at": datetime.datetime.now().isoformat()
        }

        self.appointments[sender_id].append(appointment_data)

        # Save to Firebase
        try:
            # Save appointment to Firebase
            appointment_url = f"{FIREBASE_URL}/appointments/{confirmation}.json"
            requests.put(appointment_url, json=appointment_data)
            print(f"[OK] Appointment {confirmation} saved to Firebase")
        except Exception as e:
            print(f"[WARN] Firebase save error: {e}")

        # Clear state and temp data
        self.clear_temp_data(sender_id)

        # Return confirmation message (format must match frontend parsing)
        return [{
            "recipient_id": sender_id,
            "text": f" APPOINTMENT CONFIRMED\n\n" +
                   f"Patient: {temp_data.get('patient_name')} {temp_data.get('patient_surname')}\n" +
                   f"Phone: {temp_data.get('patient_phone')}\n" +
                   f"Confirmation: {confirmation}\n" +
                   f"Department: {department}\n" +
                   f"Doctor: {selected_doctor}\n" +
                   f"Date: {date} at {time}\n" +
                   f"Location: Main Clinic, Building A\n\n" +
                   f"Please arrive 15 minutes early and bring:\n" +
                   f"• Photo ID\n" +
                   f"• Insurance card\n" +
                   f"• List of current medications\n\n" +
                   f"To cancel or reschedule, reference your confirmation number: {confirmation}",
            "buttons": [
                {"title": "View my appointments", "payload": "/view_appointments"},
                {"title": " Open calendar", "payload": "/open_calendar"},
                {"title": "Start new conversation", "payload": "/greet"}
            ]
        }]

    def process_message(self, message, sender_id):
        """Process user message and return appropriate response"""
        message_lower = message.lower()
        responses = []

        # Check if user is in a state (collecting patient info)
        current_state = self.get_user_state(sender_id)
        temp_data = self.get_temp_data(sender_id)

        # Handle state-based responses (patient info collection)
        if current_state == 'waiting_for_name':
            temp_data['patient_name'] = message.strip()
            self.set_user_state(sender_id, 'waiting_for_surname')
            responses.append({
                "recipient_id": sender_id,
                "text": "Please provide your last name:"
            })
            return responses

        elif current_state == 'waiting_for_surname':
            temp_data['patient_surname'] = message.strip()
            self.set_user_state(sender_id, 'waiting_for_phone')
            responses.append({
                "recipient_id": sender_id,
                "text": "Please provide your phone number:"
            })
            return responses

        elif current_state == 'waiting_for_phone':
            temp_data['patient_phone'] = message.strip()

            # Check if department was already assigned (from symptoms)
            if 'department' not in temp_data or not temp_data['department']:
                self.set_user_state(sender_id, 'waiting_for_department')
                responses.append({
                    "recipient_id": sender_id,
                    "text": "Which department would you like to visit?\n\n" +
                           "🏥 Available Departments:\n" +
                           "1. Cardiology - Heart & cardiovascular\n" +
                           "2. Neurology - Brain & nervous system\n" +
                           "3. General Medicine - Primary care\n" +
                           "4. Orthopedics - Bones & joints\n" +
                           "5. Pediatrics - Children's health\n" +
                           "6. Emergency - Urgent care\n\n" +
                           "Please select a department:",
                    "buttons": [
                        {"title": "Cardiology", "payload": "/select_Cardiology"},
                        {"title": "Neurology", "payload": "/select_Neurology"},
                        {"title": "General Medicine", "payload": "/select_General Medicine"},
                        {"title": "Orthopedics", "payload": "/select_Orthopedics"},
                        {"title": "Pediatrics", "payload": "/select_Pediatrics"},
                        {"title": "Emergency", "payload": "/select_Emergency"}
                    ]
                })
                return responses
            else:
                # Department already assigned, confirm appointment
                return self.confirm_appointment(sender_id, temp_data)

        elif current_state == 'waiting_for_department':
            # Extract department from message
            department = None

            # Check for /select_ payload
            if "/select_" in message:
                department = message.split("/select_")[1]
            # Check for department names in message
            elif "cardiology" in message_lower:
                department = "Cardiology"
            elif "neurology" in message_lower:
                department = "Neurology"
            elif "general medicine" in message_lower or "general" in message_lower:
                department = "General Medicine"
            elif "orthopedics" in message_lower or "orthopedic" in message_lower:
                department = "Orthopedics"
            elif "pediatrics" in message_lower or "pediatric" in message_lower:
                department = "Pediatrics"
            elif "emergency" in message_lower:
                department = "Emergency"

            if department:
                temp_data['department'] = department
                return self.confirm_appointment(sender_id, temp_data)
            else:
                responses.append({
                    "recipient_id": sender_id,
                    "text": "I didn't understand that department. Please select one from the list above."
                })
                return responses

        # Emergency detection - PRIORITY CHECK
        if any(keyword in message_lower for keyword in EMERGENCY_KEYWORDS):
            responses.append({
                "recipient_id": sender_id,
                "text": " EMERGENCY PROTOCOL ACTIVATED\n\n" +
                       "CALL 911 IMMEDIATELY\n\n" +
                       "Your symptoms require immediate medical attention:\n" +
                       "• Do NOT drive yourself to the hospital\n" +
                       "• Stay calm and still\n" +
                       "• Unlock your door for paramedics\n" +
                       "• Have someone wait outside to guide them\n\n" +
                       "Help is on the way!"
            })
            return responses  # Return immediately for emergencies

        # Ambulance request
        elif "ambulance" in message_lower:
            responses.append({
                "recipient_id": sender_id,
                "text": "🚑 AMBULANCE DISPATCHED\n\n" +
                       " CALLING 911...\n\n" +
                       "WHILE WAITING:\n" +
                       "1. Stay calm\n" +
                       "2. Unlock door if possible\n" +
                       "3. Gather medications\n\n" +
                       "ETA: 5-10 minutes\n" +
                       "Nearest hospital: Memorial Medical Center (2.3 miles)",
                "buttons": [
                    {"title": "Ambulance status", "payload": "/ambulance_status"},
                    {"title": "Cancel ambulance", "payload": "/cancel_ambulance"}
                ]
            })
            return responses

        # Type symptoms handler
        if "/type_symptoms" in message or "type symptoms" in message_lower or "type my symptoms" in message_lower:
            responses.append({
                "recipient_id": sender_id,
                "text": "Please type your symptoms in your own words. Describe:\n" +
                       "- What you're feeling\n" +
                       "- When it started\n" +
                       "- How severe it is\n" +
                       "- Any other relevant details"
            })

            return responses
        # Handle calendar-based appointment booking
        elif "book appointment for" in message_lower:
            # Extract date and time from message like "book appointment for Friday, December 27, 2024 at 14:30"
            # Parse the date and time from message
            import re
            time_match = re.search(r'at (\d{2}:\d{2})', message_lower)
            time_str = time_match.group(1) if time_match else "Unknown time"

            # Extract date (everything between "for" and "at")
            date_match = re.search(r'for (.+?) at', message_lower)
            date_str = date_match.group(1) if date_match else "Unknown date"

            # Start patient info collection
            temp_data['date'] = date_str.title()
            temp_data['time'] = time_str

            # Check if department can be auto-assigned from previous messages
            auto_dept = self.auto_assign_department(message_lower)
            if auto_dept:
                temp_data['department'] = auto_dept

            # Ask for patient name
            self.set_user_state(sender_id, 'waiting_for_name')
            responses.append({
                "recipient_id": sender_id,
                "text": f"Great! I'll help you book an appointment for {date_str.title()} at {time_str}.\n\nPlease provide your first name:"
            })
            return responses

        # Cancel appointment - Must check BEFORE general appointment
        elif "cancel" in message_lower and "appointment" in message_lower:
            if sender_id in self.appointments and self.appointments[sender_id]:
                apt_list = self.appointments[sender_id]

                # If only one appointment, cancel it directly
                if len(apt_list) == 1:
                    apt = apt_list[0]
                    self.appointments[sender_id] = []
                    responses.append({
                        "recipient_id": sender_id,
                        "text": f" APPOINTMENT CANCELLED\n\n" +
                               f"Cancelled: {apt['date']} at {apt['time']}\n" +
                               f"Doctor: {apt['doctor']}\n" +
                               f"Confirmation: {apt['id']}\n\n" +
                               f"Would you like to reschedule?",
                        "buttons": [
                            {"title": "Schedule new appointment", "payload": "/schedule_appointment"},
                            {"title": "Main menu", "payload": "/greet"}
                        ]
                    })
                else:
                    # Multiple appointments - show list to select which one to cancel
                    cancel_text = " WHICH APPOINTMENT TO CANCEL?\n\n"
                    cancel_buttons = []
                    for i, apt in enumerate(apt_list, 1):
                        cancel_text += f"{i}. {apt['date']} at {apt['time']}\n"
                        cancel_text += f"   Doctor: {apt['doctor']}\n"
                        cancel_text += f"   ID: {apt['id']}\n\n"
                        cancel_buttons.append({
                            "title": f"Cancel #{i}: {apt['date']} {apt['time']}",
                            "payload": f"/cancel_apt_{apt['id']}"
                        })

                    responses.append({
                        "recipient_id": sender_id,
                        "text": cancel_text.rstrip(),
                        "buttons": cancel_buttons[:3]  # Limit to 3 buttons
                    })
            else:
                responses.append({
                    "recipient_id": sender_id,
                    "text": "No appointments to cancel.",
                    "buttons": [
                        {"title": "Schedule appointment", "payload": "/schedule_appointment"}
                    ]
                })
            return responses

        # Handle specific appointment cancellation by ID
        elif "/cancel_apt_" in message:
            apt_id = message.split("/cancel_apt_")[1]
            if sender_id in self.appointments and self.appointments[sender_id]:
                apt_list = self.appointments[sender_id]
                cancelled_apt = None

                # Find and remove the appointment with matching ID
                for i, apt in enumerate(apt_list):
                    if apt['id'] == apt_id:
                        cancelled_apt = apt
                        apt_list.pop(i)
                        break

                if cancelled_apt:
                    responses.append({
                        "recipient_id": sender_id,
                        "text": f" APPOINTMENT CANCELLED\n\n" +
                               f"Cancelled: {cancelled_apt['date']} at {cancelled_apt['time']}\n" +
                               f"Doctor: {cancelled_apt['doctor']}\n" +
                               f"Confirmation: {cancelled_apt['id']}\n\n" +
                               f"Would you like to reschedule?",
                        "buttons": [
                            {"title": "Schedule new appointment", "payload": "/schedule_appointment"},
                            {"title": "View my appointments", "payload": "/view_appointments"},
                            {"title": "Main menu", "payload": "/greet"}
                        ]
                    })
                else:
                    responses.append({
                        "recipient_id": sender_id,
                        "text": " Appointment not found. It may have been already cancelled."
                    })
            else:
                responses.append({
                    "recipient_id": sender_id,
                    "text": "No appointments found."
                })
            return responses

        # Handle reschedule appointment request
        elif "/reschedule_apt_" in message:
            apt_id = message.split("/reschedule_apt_")[1]
            if sender_id in self.appointments and self.appointments[sender_id]:
                apt_list = self.appointments[sender_id]
                apt_to_reschedule = None

                # Find the appointment to reschedule
                for apt in apt_list:
                    if apt['id'] == apt_id:
                        apt_to_reschedule = apt
                        break

                if apt_to_reschedule:
                    # Store the appointment ID for rescheduling
                    if not hasattr(self, 'reschedule_ids'):
                        self.reschedule_ids = {}
                    self.reschedule_ids[sender_id] = apt_id

                    responses.append({
                        "recipient_id": sender_id,
                        "text": f" RESCHEDULING APPOINTMENT\n\n" +
                               f"Current: {apt_to_reschedule['date']} at {apt_to_reschedule['time']}\n" +
                               f"Doctor: {apt_to_reschedule['doctor']}\n\n" +
                               f"Select new time:",
                        "buttons": [
                            {"title": "Today 4:30 PM", "payload": "/reschedule_today_430pm"},
                            {"title": "Tomorrow 9:00 AM", "payload": "/reschedule_tomorrow_9am"},
                            {"title": "Tomorrow 2:00 PM", "payload": "/reschedule_tomorrow_2pm"}
                        ]
                    })
                else:
                    responses.append({
                        "recipient_id": sender_id,
                        "text": " Appointment not found."
                    })
            else:
                responses.append({
                    "recipient_id": sender_id,
                    "text": "No appointments to reschedule."
                })
            return responses

        # Handle reschedule time selections
        elif any(x in message for x in ["/reschedule_today_430pm", "/reschedule_tomorrow_9am", "/reschedule_tomorrow_2pm"]):
            if sender_id in self.appointments and hasattr(self, 'reschedule_ids') and sender_id in self.reschedule_ids:
                apt_id = self.reschedule_ids[sender_id]
                apt_list = self.appointments[sender_id]

                # Find and update the appointment
                for apt in apt_list:
                    if apt['id'] == apt_id:
                        old_time = f"{apt['date']} at {apt['time']}"

                        # Only update date and time, keep doctor and department the same
                        if "/reschedule_today_430pm" in message:
                            apt['date'] = "Today"
                            apt['time'] = "4:30 PM"
                        elif "/reschedule_tomorrow_9am" in message:
                            apt['date'] = "Tomorrow"
                            apt['time'] = "9:00 AM"
                        elif "/reschedule_tomorrow_2pm" in message:
                            apt['date'] = "Tomorrow"
                            apt['time'] = "2:00 PM"

                        # Update in Firebase as well
                        try:
                            appointment_url = f"{FIREBASE_URL}/appointments/{apt_id}.json"
                            requests.patch(appointment_url, json={
                                'date': apt['date'],
                                'time': apt['time']
                            })
                            print(f" Appointment {apt_id} rescheduled in Firebase")
                        except Exception as e:
                            print(f" Firebase update error: {e}")

                        responses.append({
                            "recipient_id": sender_id,
                            "text": f" APPOINTMENT RESCHEDULED\n\n" +
                                   f"Old time: {old_time}\n" +
                                   f"New time: {apt['date']} at {apt['time']}\n" +
                                   f"Department: {apt.get('department', 'N/A')}\n" +
                                   f"Doctor: {apt['doctor']}\n" +
                                   f"Confirmation: {apt['id']}",
                            "buttons": [
                                {"title": "View my appointments", "payload": "/view_appointments"},
                                {"title": "Start new conversation", "payload": "/greet"}
                            ]
                        })

                        # Clear the reschedule ID
                        del self.reschedule_ids[sender_id]
                        break
            else:
                responses.append({
                    "recipient_id": sender_id,
                    "text": " No appointment selected for rescheduling."
                })
            return responses

        # View appointments - Must check BEFORE general appointment booking
        elif ("view" in message_lower or "my" in message_lower or "/view_appointments" in message) and "appointment" in message_lower:
            if sender_id in self.appointments and self.appointments[sender_id]:
                apt_list = self.appointments[sender_id]
                apt_text = " YOUR APPOINTMENTS:\n\n"
                for i, apt in enumerate(apt_list, 1):
                    apt_text += f"{i}. {apt['date']} at {apt['time']}\n"
                    if 'department' in apt:
                        apt_text += f"   Department: {apt['department']}\n"
                    apt_text += f"   Doctor: {apt['doctor']}\n"
                    apt_text += f"   ID: {apt['id']}\n\n"

                responses.append({
                    "recipient_id": sender_id,
                    "text": apt_text.rstrip(),
                    "buttons": [
                        {"title": "Cancel appointment", "payload": "/cancel_appointment"},
                        {"title": "Add new appointment", "payload": "/schedule_appointment"}
                    ]
                })
            else:
                responses.append({
                    "recipient_id": sender_id,
                    "text": " No appointments scheduled.\n\nWould you like to schedule one?",
                    "buttons": [
                        {"title": "Schedule appointment", "payload": "/schedule_appointment"}
                    ]
                })
            return responses

        # Appointment booking
        elif any(x in message_lower for x in ["book appointment", "schedule appointment"]) or ("appointment" in message_lower and "view" not in message_lower and "my" not in message_lower and "cancel" not in message_lower):
            responses.append({
                "recipient_id": sender_id,
                "text": " APPOINTMENT SCHEDULING\n\n" +
                       "Available slots:\n" +
                       "• Today 4:30 PM\n" +
                       "• Tomorrow 9:00 AM\n" +
                       "• Tomorrow 2:00 PM\n\n" +
                       "Please select your preferred time:",
                "buttons": [
                    {"title": "Today 4:30 PM", "payload": "/book_today_430pm"},
                    {"title": "Tomorrow 9:00 AM", "payload": "/book_tomorrow_9am"},
                    {"title": "Tomorrow 2:00 PM", "payload": "/book_tomorrow_2pm"},
                    {"title": " Open Calendar", "payload": "/open_calendar"}
                ]
            })
            return responses

        # Specific appointment times
        elif "today 4:30" in message_lower or "/book_today_430pm" in message:
            # Start patient info collection
            temp_data['date'] = "Today"
            temp_data['time'] = "4:30 PM"

            # Check if department can be auto-assigned from previous messages
            # (in a real implementation, you'd track symptom history)
            auto_dept = self.auto_assign_department(message_lower)
            if auto_dept:
                temp_data['department'] = auto_dept

            # Ask for patient name
            self.set_user_state(sender_id, 'waiting_for_name')
            responses.append({
                "recipient_id": sender_id,
                "text": "Great! I'll help you book an appointment for Today at 4:30 PM.\n\nPlease provide your first name:"
            })
            return responses

        elif "tomorrow 9:00" in message_lower or "/book_tomorrow_9am" in message:
            # Start patient info collection
            temp_data['date'] = "Tomorrow"
            temp_data['time'] = "9:00 AM"

            # Check if department can be auto-assigned from previous messages
            auto_dept = self.auto_assign_department(message_lower)
            if auto_dept:
                temp_data['department'] = auto_dept

            # Ask for patient name
            self.set_user_state(sender_id, 'waiting_for_name')
            responses.append({
                "recipient_id": sender_id,
                "text": "Great! I'll help you book an appointment for Tomorrow at 9:00 AM.\n\nPlease provide your first name:"
            })
            return responses

        elif "tomorrow 2:00" in message_lower or "/book_tomorrow_2pm" in message:
            # Start patient info collection
            temp_data['date'] = "Tomorrow"
            temp_data['time'] = "2:00 PM"

            # Check if department can be auto-assigned from previous messages
            auto_dept = self.auto_assign_department(message_lower)
            if auto_dept:
                temp_data['department'] = auto_dept

            # Ask for patient name
            self.set_user_state(sender_id, 'waiting_for_name')
            responses.append({
                "recipient_id": sender_id,
                "text": "Great! I'll help you book an appointment for Tomorrow at 2:00 PM.\n\nPlease provide your first name:"
            })
            return responses

        # Symptom assessment
        elif any(keyword in message_lower for keyword in ["fever", "headache", "cough", "stomach"]):
            symptom = ""
            advice = ""

            if "fever" in message_lower:
                symptom = "FEVER"
                advice = ("📊 Temperature Guide:\n" +
                         "• 98-99°F - Normal\n" +
                         "• 99-100.4°F - Low-grade fever\n" +
                         "• 100.4-103°F - Moderate fever (see doctor)\n" +
                         "• Above 103°F - High fever (urgent care)\n\n" +
                         "Monitor temperature every 4 hours")

            elif "headache" in message_lower:
                symptom = "HEADACHE"
                advice = ("📍 Location & Type:\n" +
                         "• Tension: Band around head\n" +
                         "• Migraine: One-sided, throbbing\n" +
                         "• Cluster: Behind eye\n\n" +
                         " Seek care if:\n" +
                         "• Sudden severe headache\n" +
                         "• With fever and stiff neck\n" +
                         "• After head injury")

            elif "cough" in message_lower:
                symptom = "COUGH"
                advice = ("🔍 Type of cough:\n" +
                         "• Dry cough - No phlegm\n" +
                         "• Productive - With phlegm\n\n" +
                         "⏱ Duration:\n" +
                         "• < 3 weeks: Acute (usually viral)\n" +
                         "• > 3 weeks: Chronic (see doctor)\n\n" +
                         "Self-care: Honey, warm fluids, humidifier")

            elif "stomach" in message_lower:
                symptom = "STOMACH PAIN"
                advice = ("📍 Location matters:\n" +
                         "• Upper right: Gallbladder\n" +
                         "• Upper center: Stomach/ulcer\n" +
                         "• Lower right: Appendix (URGENT)\n\n" +
                         " URGENT if:\n" +
                         "• Severe sudden pain\n" +
                         "• With high fever\n" +
                         "• Can't pass gas/stool")

            # Check severity
            if any(keyword in message_lower for keyword in URGENT_KEYWORDS):
                triage = "URGENT CARE NEEDED"
                action_buttons = [
                    {"title": "Go to urgent care", "payload": "/urgent_care"},
                    {"title": "Call ambulance", "payload": "/call_ambulance"}
                ]
            else:
                triage = "GP APPOINTMENT RECOMMENDED"
                action_buttons = [
                    {"title": "Book GP appointment", "payload": "/schedule_appointment"},
                    {"title": "Self-care advice", "payload": "/self_care"}
                ]

            responses.append({
                "recipient_id": sender_id,
                "text": f"{symptom} ASSESSMENT\n\n{advice}\n\nRecommendation: {triage}",
                "buttons": action_buttons
            })
            return responses

        # Self-care advice - enhanced with specific conditions
        elif "self-care" in message_lower or "self care" in message_lower or "/self_care" in message:
            # Check if coming from specific condition
            condition_specific = False

            # Cold/flu self-care
            if "/self_care_cold" in message:
                condition_specific = True
                responses.append({
                    "recipient_id": sender_id,
                    "text": "🤧 COLD & FLU SELF-CARE\n\n" +
                           " RECOMMENDED ACTIONS:\n\n" +
                           "💊 MEDICATION:\n" +
                           "• Paracetamol for fever/pain (max 4g daily)\n" +
                           "• Ibuprofen for inflammation (with food)\n" +
                           "• Throat lozenges for sore throat\n" +
                           "• Decongestants for blocked nose\n\n" +
                           "🏠 HOME REMEDIES:\n" +
                           "• Warm salt water gargle (3x daily)\n" +
                           "• Steam inhalation with eucalyptus\n" +
                           "• Honey and lemon in warm water\n" +
                           "• Chicken soup for nutrition\n\n" +
                           "💧 HYDRATION:\n" +
                           "• 2-3 liters of fluids daily\n" +
                           "• Warm herbal teas\n" +
                           "• Avoid alcohol completely\n\n" +
                           "🛌 REST:\n" +
                           "• Sleep 8-10 hours\n" +
                           "• Stay home from work/school\n" +
                           "• Avoid spreading to others\n\n" +
                           " SEE DOCTOR IF:\n" +
                           "• Fever >39°C for 3+ days\n" +
                           "• Difficulty breathing\n" +
                           "• Chest pain or pressure\n" +
                           "• Severe headache or confusion",
                    "buttons": [
                        {"title": "Track my symptoms", "payload": "/symptom_tracker"},
                        {"title": "When to see doctor", "payload": "/when_to_see_doctor"},
                        {"title": "Book appointment", "payload": "/schedule_appointment"}
                    ]
                })
                return responses
            # Headache self-care
            if "/self_care_headache" in message:
                condition_specific = True
                responses.append({
                    "recipient_id": sender_id,
                    "text": "🤕 HEADACHE SELF-CARE\n\n" +
                           " IMMEDIATE RELIEF:\n\n" +
                           "💊 MEDICATION:\n" +
                           "• Paracetamol 1g (first choice)\n" +
                           "• Ibuprofen 400mg (if needed)\n" +
                           "• Aspirin 900mg (alternative)\n" +
                           "• Avoid overuse (max 10 days/month)\n\n" +
                           "🏠 NON-DRUG RELIEF:\n" +
                           "• Apply cold compress to head/neck\n" +
                           "• Rest in dark, quiet room\n" +
                           "• Gentle neck stretches\n" +
                           "• Scalp/temple massage\n\n" +
                           "💧 LIFESTYLE:\n" +
                           "• Drink 2L water immediately\n" +
                           "• Regular meal times\n" +
                           "• Limit screen time\n" +
                           "• Avoid bright lights\n\n" +
                           "😴 PREVENTION:\n" +
                           "• Sleep 7-9 hours nightly\n" +
                           "• Manage stress levels\n" +
                           "• Regular exercise\n" +
                           "• Identify triggers\n\n" +
                           " SEEK HELP IF:\n" +
                           "• Sudden, severe headache\n" +
                           "• With fever and stiff neck\n" +
                           "• Vision changes\n" +
                           "• After head injury",
                    "buttons": [
                        {"title": "Headache diary", "payload": "/headache_diary"},
                        {"title": "Migraine assessment", "payload": "/migraine_check"},
                        {"title": "Book appointment", "payload": "/schedule_appointment"}
                    ]
                })
                return responses
            # Stomach upset self-care
            if "/self_care_stomach" in message:
                condition_specific = True
                responses.append({
                    "recipient_id": sender_id,
                    "text": "🤢 STOMACH UPSET SELF-CARE\n\n" +
                           " RELIEF MEASURES:\n\n" +
                           "🍽 DIET (BRAT):\n" +
                           "• Bananas (potassium)\n" +
                           "• Rice (plain, white)\n" +
                           "• Applesauce (pectin)\n" +
                           "• Toast (dry, plain)\n\n" +
                           "💊 MEDICATION:\n" +
                           "• Antacids for heartburn\n" +
                           "• Buscopan for cramps\n" +
                           "• Imodium for diarrhea\n" +
                           "• Avoid NSAIDs\n\n" +
                           "💧 HYDRATION:\n" +
                           "• Small, frequent sips\n" +
                           "• Electrolyte solutions\n" +
                           "• Ginger or peppermint tea\n" +
                           "• Avoid dairy products\n\n" +
                           "🚫 AVOID:\n" +
                           "• Fatty/fried foods\n" +
                           "• Spicy foods\n" +
                           "• Caffeine & alcohol\n" +
                           "• Large meals\n\n" +
                           " SEE DOCTOR IF:\n" +
                           "• Blood in vomit/stool\n" +
                           "• Severe dehydration\n" +
                           "• Pain lasting >24 hours\n" +
                           "• High fever (>38.5°C)",
                    "buttons": [
                        {"title": "Food poisoning info", "payload": "/food_poisoning"},
                        {"title": "When to see doctor", "payload": "/when_to_see_doctor"},
                        {"title": "Book appointment", "payload": "/schedule_appointment"}
                    ]
                })
                return responses
            # Back pain self-care
            if "/self_care_back" in message:
                condition_specific = True
                responses.append({
                    "recipient_id": sender_id,
                    "text": "🔙 BACK PAIN SELF-CARE\n\n" +
                           " PAIN MANAGEMENT:\n\n" +
                           "💊 MEDICATION:\n" +
                           "• Ibuprofen 400mg (3x daily with food)\n" +
                           "• Paracetamol 1g (4x daily max)\n" +
                           "• Topical heat/cold gel\n" +
                           "• Muscle relaxants (if prescribed)\n\n" +
                           "🏃 MOVEMENT:\n" +
                           "• Stay active - bed rest delays recovery\n" +
                           "• Gentle stretching exercises\n" +
                           "• Walking 10-15 minutes hourly\n" +
                           "• Swimming if possible\n\n" +
                           "🔥❄ TEMPERATURE THERAPY:\n" +
                           "• Ice first 48 hours (20 min sessions)\n" +
                           "• Heat after 48 hours\n" +
                           "• Warm baths with Epsom salt\n" +
                           "• Alternating hot/cold\n\n" +
                           "😴 SLEEPING POSITION:\n" +
                           "• Side: pillow between knees\n" +
                           "• Back: pillow under knees\n" +
                           "• Avoid stomach sleeping\n" +
                           "• Firm mattress support\n\n" +
                           " RED FLAGS - A&E NOW:\n" +
                           "• Loss of bladder/bowel control\n" +
                           "• Leg weakness or numbness\n" +
                           "• Severe pain at night\n" +
                           "• After significant trauma",
                    "buttons": [
                        {"title": "Back exercises", "payload": "/back_exercises"},
                        {"title": "Physiotherapy referral", "payload": "/physio_referral"},
                        {"title": "Book appointment", "payload": "/schedule_appointment"}
                    ]
                })

                return responses
            # General self-care (if no specific condition)
            if not condition_specific:
                responses.append({
                    "recipient_id": sender_id,
                    "text": "🏠 SELF-CARE OPTIONS\n\n" +
                           "Select specific guidance for your condition:\n\n" +
                           "Common conditions we can help with:\n" +
                           "• Cold & flu symptoms\n" +
                           "• Headaches & migraines\n" +
                           "• Stomach upset & nausea\n" +
                           "• Back pain & muscle aches\n\n" +
                           "Or choose general self-care advice below.",
                    "buttons": [
                        {"title": "Cold & flu care", "payload": "/self_care_cold"},
                        {"title": "Headache relief", "payload": "/self_care_headache"},
                        {"title": "Stomach upset", "payload": "/self_care_stomach"},
                        {"title": "Back pain help", "payload": "/self_care_back"}
                    ]
                })

                # Add general advice as follow-up
                responses.append({
                    "recipient_id": sender_id,
                    "text": "📋 GENERAL SELF-CARE GUIDELINES\n\n" +
                           "💊 SAFE MEDICATION USE:\n" +
                           "• Read labels carefully\n" +
                           "• Don't exceed recommended doses\n" +
                           "• Check drug interactions\n" +
                           "• Keep medication list updated\n\n" +
                           "💧 HYDRATION:\n" +
                           "• 8-10 glasses water daily\n" +
                           "• More if fever/vomiting\n" +
                           "• Clear fluids preferred\n\n" +
                           "🛌 REST & RECOVERY:\n" +
                           "• 7-9 hours sleep\n" +
                           "• Take time off if needed\n" +
                           "• Gradual return to activity\n\n" +
                           "🌡 MONITORING:\n" +
                           "• Keep symptom diary\n" +
                           "• Check temperature 2x daily\n" +
                           "• Note any changes\n\n" +
                           " Seek medical help if symptoms worsen or persist!",
                    "buttons": [
                        {"title": "When to see doctor", "payload": "/when_to_see_doctor"},
                        {"title": "Schedule appointment", "payload": "/schedule_appointment"},
                        {"title": "Main menu", "payload": "/greet"}
                    ]
                })
            return responses

        # Describe symptoms
        elif "describe symptom" in message_lower or "/describe_symptoms" in message or "i have symptoms" in message_lower:
            responses.append({
                "recipient_id": sender_id,
                "text": "📋 SYMPTOM ASSESSMENT\n\n" +
                       "Please describe your symptoms. I can help with:\n\n" +
                       "• Pain (head, chest, stomach, back)\n" +
                       "• Respiratory (cough, breathing issues)\n" +
                       "• Fever/chills\n" +
                       "• Nausea/vomiting\n" +
                       "• Dizziness/fatigue\n" +
                       "• Rash/skin issues\n\n" +
                       "Tell me:\n" +
                       "1. What symptoms are you experiencing?\n" +
                       "2. How long have you had them?\n" +
                       "3. Rate severity (1-10)\n" +
                       "4. Any other symptoms?",
                "buttons": [
                    {"title": "Mild symptoms", "payload": "/mild_symptoms"},
                    {"title": "Moderate symptoms", "payload": "/moderate_symptoms"},
                    {"title": "Severe symptoms", "payload": "/severe_symptoms"},
                    {"title": "Type my symptoms", "payload": "/type_symptoms"}
                ]
            })
            return responses

        # Mild symptoms
        elif "mild symptom" in message_lower or "/mild_symptoms" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🟢 MILD SYMPTOMS ASSESSMENT\n\n" +
                       "Let me help you determine the best care approach.\n\n" +
                       "What type of mild symptoms are you experiencing?\n\n" +
                       "Common mild symptoms:\n" +
                       "• Runny nose / congestion\n" +
                       "• Mild headache\n" +
                       "• Sore throat\n" +
                       "• Minor aches and pains\n" +
                       "• Mild fatigue\n" +
                       "• Low-grade fever (<100.4°F)\n\n" +
                       "How long have you had these symptoms?",
                "buttons": [
                    {"title": "Cold/flu symptoms", "payload": "/mild_cold_flu"},
                    {"title": "Mild headache", "payload": "/mild_headache"},
                    {"title": "Minor digestive issues", "payload": "/mild_digestive"},
                    {"title": "General fatigue", "payload": "/mild_fatigue"},
                    {"title": "Type my symptoms", "payload": "/type_symptoms"}
                ]
            })
            return responses

        # Mild cold/flu symptoms
        if "/mild_cold_flu" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🤧 MILD COLD/FLU CARE\n\n" +
                       "Your symptoms suggest a common cold or mild flu.\n\n" +
                       "HOME CARE PLAN:\n\n" +
                       "💊 Medications:\n" +
                       "• Acetaminophen for fever/aches\n" +
                       "• Decongestants for stuffy nose\n" +
                       "• Throat lozenges for sore throat\n\n" +
                       "🏠 Self-care:\n" +
                       "• Rest - get 8+ hours sleep\n" +
                       "• Fluids - drink warm tea, soup\n" +
                       "• Steam inhalation for congestion\n" +
                       "• Wash hands frequently\n\n" +
                       " See doctor if:\n" +
                       "• Fever > 103°F for 3+ days\n" +
                       "• Difficulty breathing\n" +
                       "• Chest pain\n" +
                       "• Symptoms worsen after 7 days",
                "buttons": [
                    {"title": "More self-care tips", "payload": "/self_care"},
                    {"title": "When to see doctor", "payload": "/when_to_see_doctor"},
                    {"title": "Type my symptoms", "payload": "/type_symptoms"}
                ]
            })

            return responses
        # Mild digestive issues
        if "/mild_digestive" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🤢 MILD DIGESTIVE ISSUES\n\n" +
                       "Common digestive discomfort management:\n\n" +
                       "IMMEDIATE RELIEF:\n" +
                       "• Small sips of water\n" +
                       "• Ginger tea or peppermint tea\n" +
                       "• BRAT diet (Bananas, Rice, Applesauce, Toast)\n" +
                       "• Avoid fatty/spicy foods\n\n" +
                       "MEDICATIONS:\n" +
                       "• Antacids for heartburn\n" +
                       "• Simethicone for gas\n" +
                       "• Loperamide for diarrhea\n\n" +
                       " See doctor if:\n" +
                       "• Blood in stool/vomit\n" +
                       "• Severe dehydration\n" +
                       "• Pain lasting > 24 hours\n" +
                       "• Fever with symptoms",
                "buttons": [
                    {"title": "Hydration tips", "payload": "/hydration_tips"},
                    {"title": "When to worry", "payload": "/when_to_see_doctor"},
                    {"title": "Type my symptoms", "payload": "/type_symptoms"}
                ]
            })

            return responses
        # Mild fatigue
        if "/mild_fatigue" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "😴 MILD FATIGUE ASSESSMENT\n\n" +
                       "Fatigue can have many causes. Let's explore:\n\n" +
                       "LIFESTYLE FACTORS:\n" +
                       "• Sleep: Are you getting 7-9 hours?\n" +
                       "• Hydration: Drinking enough water?\n" +
                       "• Diet: Eating balanced meals?\n" +
                       "• Exercise: Too much or too little?\n\n" +
                       "SELF-CARE PLAN:\n" +
                       "• Maintain regular sleep schedule\n" +
                       "• Limit caffeine after 2 PM\n" +
                       "• Take short walks\n" +
                       "• Manage stress\n\n" +
                       " See doctor if:\n" +
                       "• Fatigue > 2 weeks\n" +
                       "• With unexplained weight loss\n" +
                       "• With fever or pain\n" +
                       "• Affecting daily life",
                "buttons": [
                    {"title": "Sleep hygiene tips", "payload": "/sleep_tips"},
                    {"title": "Energy boosting tips", "payload": "/energy_tips"},
                    {"title": "Type my symptoms", "payload": "/type_symptoms"}
                ]
            })

            return responses
        # Mild headache
        if "/mild_headache" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🤕 MILD HEADACHE MANAGEMENT\n\n" +
                       "Most mild headaches can be managed at home.\n\n" +
                       "IMMEDIATE RELIEF:\n" +
                       "• Take ibuprofen or acetaminophen\n" +
                       "• Apply cold compress to head\n" +
                       "• Rest in dark, quiet room\n" +
                       "• Stay hydrated\n\n" +
                       "COMMON TRIGGERS TO AVOID:\n" +
                       "• Dehydration\n" +
                       "• Eye strain (screens)\n" +
                       "• Poor posture\n" +
                       "• Stress\n" +
                       "• Skipping meals\n\n" +
                       " Seek care if:\n" +
                       "• Sudden severe headache\n" +
                       "• With fever and stiff neck\n" +
                       "• After head injury\n" +
                       "• Vision changes",
                "buttons": [
                    {"title": "Track symptoms", "payload": "/symptom_diary"},
                    {"title": "Relaxation techniques", "payload": "/relaxation"},
                    {"title": "Type my symptoms", "payload": "/type_symptoms"}
                ]
            })

            return responses
        # Moderate breathing concerns
        if "/moderate_breathing" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🫁 MODERATE BREATHING CONCERNS\n\n" +
                       "Breathing issues need careful monitoring.\n\n" +
                       "ASSESSMENT:\n" +
                       "• Can you walk and talk normally?\n" +
                       "• Is it worse with activity?\n" +
                       "• Any wheezing or coughing?\n" +
                       "• History of asthma/allergies?\n\n" +
                       "IMMEDIATE ACTIONS:\n" +
                       "• Sit upright\n" +
                       "• Use inhaler if prescribed\n" +
                       "• Avoid triggers (smoke, allergens)\n" +
                       "• Monitor oxygen if available\n\n" +
                       "SEE DOCTOR TODAY if:\n" +
                       "• Not improving with rest\n" +
                       "• New onset without clear cause\n" +
                       "• With chest pain or fever",
                "buttons": [
                    {"title": "Book urgent appointment", "payload": "/schedule_appointment"},
                    {"title": "Breathing exercises", "payload": "/breathing_exercises"},
                    {"title": "When to call 911", "payload": "/emergency_signs"},
                    {"title": "Type my symptoms", "payload": "/type_symptoms"}
                ]
            })
            return responses

        # Multiple moderate symptoms
        if "/moderate_multiple" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "📋 MULTIPLE SYMPTOMS ASSESSMENT\n\n" +
                       "Having several symptoms may indicate systemic illness.\n\n" +
                       "PLEASE LIST YOUR SYMPTOMS:\n" +
                       "Type all symptoms you're experiencing\n" +
                       "(e.g., fever, headache, cough, fatigue)\n\n" +
                       "IMPORTANT TO NOTE:\n" +
                       "• When symptoms started\n" +
                       "• Order of appearance\n" +
                       "• Severity of each (1-10)\n" +
                       "• What makes better/worse\n\n" +
                       "Multiple symptoms often need medical evaluation\n" +
                       "to rule out infection or other conditions.",
                "buttons": [
                    {"title": "See doctor today", "payload": "/schedule_appointment"},
                    {"title": "Speak to nurse now", "payload": "/nurse"},
                    {"title": "Emergency signs", "payload": "/emergency_signs"},
                    {"title": "Type my symptoms", "payload": "/type_symptoms"}
                ]
            })

            return responses
        # Moderate symptoms
        elif "moderate symptom" in message_lower or "/moderate_symptoms" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🟡 MODERATE SYMPTOMS ASSESSMENT\n\n" +
                       "Your symptoms need careful evaluation.\n\n" +
                       "Which best describes your condition?\n\n" +
                       "🔸 PERSISTENT SYMPTOMS:\n" +
                       "• Symptoms lasting 3-7 days\n" +
                       "• Not improving with self-care\n" +
                       "• Moderate pain (4-6/10)\n\n" +
                       "🔸 WORSENING SYMPTOMS:\n" +
                       "• Started mild, getting worse\n" +
                       "• New symptoms developing\n" +
                       "• Interfering with daily activities\n\n" +
                       "🔸 CONCERNING SIGNS:\n" +
                       "• Moderate fever (101-103°F)\n" +
                       "• Persistent cough\n" +
                       "• Moderate breathing difficulty",
                "buttons": [
                    {"title": "Persistent fever/infection", "payload": "/moderate_infection"},
                    {"title": "Worsening pain", "payload": "/moderate_pain"},
                    {"title": "Breathing concerns", "payload": "/moderate_breathing"},
                    {"title": "Multiple symptoms", "payload": "/moderate_multiple"},
                    {"title": "Type my symptoms", "payload": "/type_symptoms"}
                ]
            })
            return responses

        # Moderate infection
        if "/moderate_infection" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🦠 MODERATE INFECTION ASSESSMENT\n\n" +
                       "Your symptoms suggest possible infection needing treatment.\n\n" +
                       "RECOMMENDATION: See doctor within 24 hours\n\n" +
                       "Why you need medical care:\n" +
                       "• May need antibiotics\n" +
                       "• Risk of complications\n" +
                       "• Need proper diagnosis\n\n" +
                       "Meanwhile:\n" +
                       "• Continue fever management\n" +
                       "• Stay hydrated\n" +
                       "• Rest completely\n" +
                       "• Isolate from others\n\n" +
                       " Go to ER if:\n" +
                       "• Fever > 104°F\n" +
                       "• Difficulty breathing\n" +
                       "• Confusion\n" +
                       "• Severe dehydration",
                "buttons": [
                    {"title": "Book urgent appointment", "payload": "/schedule_appointment"},
                    {"title": "Find walk-in clinic", "payload": "/urgent_care"},
                    {"title": "Video consultation", "payload": "/telemedicine"},
                    {"title": "Type my symptoms", "payload": "/type_symptoms"}
                ]
            })

            return responses
        # Moderate pain
        if "/moderate_pain" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "😰 MODERATE PAIN EVALUATION\n\n" +
                       "Pain that's worsening needs medical attention.\n\n" +
                       "PAIN ASSESSMENT:\n" +
                       "Please rate your pain level below:\n\n" +
                       "IMMEDIATE STEPS:\n" +
                       "1. Take prescribed pain medication\n" +
                       "2. Apply ice/heat as appropriate\n" +
                       "3. Rest affected area\n" +
                       "4. Document pain patterns\n\n" +
                       "SEE DOCTOR TODAY IF:\n" +
                       "• Pain increasing despite medication\n" +
                       "• New numbness or tingling\n" +
                       "• Swelling or redness\n" +
                       "• Can't perform daily tasks",
                "buttons": [
                    {"title": "Book same-day appointment", "payload": "/schedule_appointment"},
                    {"title": "Pain management tips", "payload": "/pain_management"},
                    {"title": "Speak to nurse", "payload": "/nurse"},
                    {"title": "Type my symptoms", "payload": "/type_symptoms"}
                ]
            })

            return responses
        # Severe symptoms
        elif "severe symptom" in message_lower or "/severe_symptoms" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": " SEVERE SYMPTOMS - DETAILED ASSESSMENT\n\n" +
                       "I need to ask you some important questions to determine the right care:\n\n" +
                       "Which of these are you experiencing?\n\n" +
                       "🔴 EMERGENCY SYMPTOMS:\n" +
                       "• Chest pain or pressure\n" +
                       "• Difficulty breathing\n" +
                       "• Loss of consciousness\n" +
                       "• Severe bleeding\n\n" +
                       "🟡 URGENT SYMPTOMS:\n" +
                       "• Severe pain (8-10/10)\n" +
                       "• High fever (>103°F)\n" +
                       "• Persistent vomiting\n" +
                       "• Confusion or disorientation\n\n" +
                       "Please select your primary symptom:",
                "buttons": [
                    {"title": "Chest pain", "payload": "/chest_pain"},
                    {"title": "Breathing difficulty", "payload": "/breathing_difficulty"},
                    {"title": "Severe pain", "payload": "/severe_pain"},
                    {"title": "High fever", "payload": "/high_fever"},
                    {"title": "Type my symptoms", "payload": "/type_symptoms"}
                ]
            })
            return responses

        # Chest pain assessment
        elif "chest pain" in message_lower or "/chest_pain" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🔴 CHEST PAIN ASSESSMENT\n\n" +
                       "This could be serious. Please answer:\n\n" +
                       "How long have you had chest pain?\n" +
                       "• Just started (< 15 minutes)\n" +
                       "• Less than 1 hour\n" +
                       "• Several hours\n" +
                       "• More than a day\n\n" +
                       "What does it feel like?\n" +
                       "• Crushing/pressure\n" +
                       "• Sharp/stabbing\n" +
                       "• Burning sensation\n\n" +
                       "Associated symptoms?\n" +
                       "• Shortness of breath\n" +
                       "• Sweating\n" +
                       "• Nausea\n" +
                       "• Pain in arm/jaw",
                "buttons": [
                    {"title": "It's crushing with sweating", "payload": "/emergency_chest_pain"},
                    {"title": "Sharp when breathing", "payload": "/pleuritic_pain"},
                    {"title": "Burning after eating", "payload": "/gerd_pain"},
                    {"title": "I'm not sure", "payload": "/unsure_chest_pain"},
                    {"title": "Type my symptoms", "payload": "/type_symptoms"}
                ]
            })
            return responses

        # Emergency chest pain
        if "/emergency_chest_pain" in message or "/unsure_chest_pain" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": " EMERGENCY - POSSIBLE HEART ATTACK\n\n" +
                       "CALL 911 IMMEDIATELY!\n\n" +
                       "While waiting for ambulance:\n" +
                       "1. Chew aspirin (325mg) if available\n" +
                       "2. Sit upright, stay calm\n" +
                       "3. Unlock your door\n" +
                       "4. Have someone wait outside\n\n" +
                       "Do NOT drive yourself!\n\n" +
                       "If symptoms worsen, call 911 again.",
                "buttons": [
                    {"title": "Call 911 now", "payload": "/call_911"},
                    {"title": "I called 911", "payload": "/called_911"},
                    {"title": "Type my symptoms", "payload": "/type_symptoms"}
                ]
            })

            return responses
        # Non-emergency chest pain
        if "/pleuritic_pain" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "📋 PLEURITIC CHEST PAIN\n\n" +
                       "Your pain pattern suggests possible:\n" +
                       "• Pleurisy (lung lining inflammation)\n" +
                       "• Muscle strain\n" +
                       "• Rib injury\n\n" +
                       "Recommendation: See doctor TODAY\n\n" +
                       "Go to ER if:\n" +
                       "• Sudden severe shortness of breath\n" +
                       "• Coughing blood\n" +
                       "• Fever > 103°F\n" +
                       "• Pain worsens rapidly\n\n" +
                       "Meanwhile:\n" +
                       "• Rest\n" +
                       "• Anti-inflammatory medicine\n" +
                       "• Monitor breathing",
                "buttons": [
                    {"title": "Book urgent appointment", "payload": "/schedule_appointment"},
                    {"title": "Find urgent care", "payload": "/urgent_care"},
                    {"title": "Speak to nurse", "payload": "/nurse"},
                    {"title": "Type my symptoms", "payload": "/type_symptoms"}
                ]
            })

            return responses
        if "/gerd_pain" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "💊 LIKELY HEARTBURN/GERD\n\n" +
                       "Your symptoms suggest acid reflux.\n\n" +
                       "Try these immediately:\n" +
                       "• Antacids (Tums, Mylanta)\n" +
                       "• Sit upright\n" +
                       "• Loosen tight clothing\n" +
                       "• Sip water slowly\n\n" +
                       "See doctor if:\n" +
                       "• Pain doesn't improve in 30 min\n" +
                       "• Frequent episodes (>2x/week)\n" +
                       "• Difficulty swallowing\n" +
                       "• Unexplained weight loss\n\n" +
                       "Avoid:\n" +
                       "• Lying down\n" +
                       "• Spicy/acidic foods\n" +
                       "• Coffee and alcohol",
                "buttons": [
                    {"title": "Book GP appointment", "payload": "/schedule_appointment"},
                    {"title": "Self-care tips", "payload": "/self_care"},
                    {"title": "Type my symptoms", "payload": "/type_symptoms"}
                ]
            })

            return responses
        # Breathing difficulty assessment
        elif "breathing difficulty" in message_lower or "/breathing_difficulty" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🫁 BREATHING ASSESSMENT\n\n" +
                       "How severe is your breathing difficulty?\n\n" +
                       "Can you:\n" +
                       "• Speak in full sentences?\n" +
                       "• Walk across the room?\n" +
                       "• Lie flat?\n\n" +
                       "When did it start?\n" +
                       "• Suddenly (minutes ago)\n" +
                       "• Gradually (hours/days)\n\n" +
                       "Associated symptoms:\n" +
                       "• Chest pain?\n" +
                       "• Wheezing?\n" +
                       "• Fever?\n" +
                       "• Swollen legs?",
                "buttons": [
                    {"title": "Can't speak full sentences", "payload": "/emergency_breathing"},
                    {"title": "Wheezing, known asthma", "payload": "/asthma_attack"},
                    {"title": "Gradual with fever", "payload": "/respiratory_infection"},
                    {"title": "Anxiety/panic feeling", "payload": "/anxiety_breathing"},
                    {"title": "Type my symptoms", "payload": "/type_symptoms"}
                ]
            })
            return responses

        # Emergency breathing
        if "/emergency_breathing" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": " EMERGENCY - SEVERE BREATHING DIFFICULTY\n\n" +
                       "CALL 911 NOW!\n\n" +
                       "While waiting:\n" +
                       "• Sit upright, lean forward\n" +
                       "• Use rescue inhaler if you have one\n" +
                       "• Stay calm, breathe slowly\n" +
                       "• Open windows for fresh air\n" +
                       "• Loosen tight clothing\n\n" +
                       "Someone should stay with you!",
                "buttons": [
                    {"title": "Call 911", "payload": "/call_911"},
                    {"title": "I called 911", "payload": "/called_911"},
                    {"title": "Type my symptoms", "payload": "/type_symptoms"}
                ]
            })

            return responses

        # Respiratory infection (gradual with fever)
        if "/respiratory_infection" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🦠 RESPIRATORY INFECTION ASSESSMENT\n\n" +
                       "Gradual breathing difficulty with fever suggests possible:\n" +
                       "• Pneumonia\n" +
                       "• Bronchitis\n" +
                       "• Severe flu\n\n" +
                       "⚠️ SEE DOCTOR TODAY if:\n" +
                       "• Fever > 101°F (38.3°C)\n" +
                       "• Breathing getting worse\n" +
                       "• Coughing up colored mucus\n" +
                       "• Chest pain when breathing\n\n" +
                       "IMMEDIATE CARE:\n" +
                       "• Rest and stay hydrated\n" +
                       "• Monitor temperature\n" +
                       "• Use humidifier\n" +
                       "• Avoid cold air\n\n" +
                       "What would you like to do?",
                "buttons": [
                    {"title": "Book urgent GP appointment", "payload": "/urgent_appointment"},
                    {"title": "Self-care advice", "payload": "/respiratory_self_care"},
                    {"title": "When to go to A&E", "payload": "/respiratory_emergency_signs"},
                    {"title": "Speak to nurse", "payload": "/nurse"}
                ]
            })
            return responses

        # Respiratory self-care advice
        if "/respiratory_self_care" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🏠 RESPIRATORY INFECTION SELF-CARE\n\n" +
                       "HYDRATION:\n" +
                       "• Drink 8-10 glasses of fluids daily\n" +
                       "• Warm liquids (tea, soup, broth)\n" +
                       "• Avoid alcohol and caffeine\n\n" +
                       "BREATHING SUPPORT:\n" +
                       "• Use humidifier or steam inhalation\n" +
                       "• Sleep with head elevated\n" +
                       "• Practice deep breathing exercises\n\n" +
                       "REST:\n" +
                       "• Stay home from work/school\n" +
                       "• Sleep 8-10 hours\n" +
                       "• Avoid strenuous activity\n\n" +
                       "FEVER MANAGEMENT:\n" +
                       "• Paracetamol/Ibuprofen as directed\n" +
                       "• Cool compress on forehead\n" +
                       "• Monitor temperature 2x daily",
                "buttons": [
                    {"title": "Book GP appointment", "payload": "/schedule_appointment"},
                    {"title": "When to seek emergency care", "payload": "/respiratory_emergency_signs"},
                    {"title": "Main menu", "payload": "/main_menu"}
                ]
            })
            return responses

        # Respiratory emergency warning signs
        if "/respiratory_emergency_signs" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🚨 GO TO A&E IMMEDIATELY IF:\n\n" +
                       "SEVERE BREATHING:\n" +
                       "• Can't speak full sentences\n" +
                       "• Gasping for air\n" +
                       "• Blue lips or face\n" +
                       "• Chest pulling in with breaths\n\n" +
                       "HIGH FEVER:\n" +
                       "• Temperature > 104°F (40°C)\n" +
                       "• Fever with severe headache\n" +
                       "• Stiff neck + confusion\n\n" +
                       "OTHER RED FLAGS:\n" +
                       "• Coughing up blood\n" +
                       "• Severe chest pain\n" +
                       "• Drowsiness/confusion\n" +
                       "• Can't keep fluids down\n\n" +
                       "CALL 999 if any of the above!",
                "buttons": [
                    {"title": "Find nearest A&E", "payload": "/find_ae"},
                    {"title": "Call 999", "payload": "/call_999"},
                    {"title": "Speak to nurse now", "payload": "/nurse"}
                ]
            })
            return responses

        # Severe pain assessment
        elif "severe pain" in message_lower or "/severe_pain" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "😣 SEVERE PAIN ASSESSMENT\n\n" +
                       "Where is your severe pain located?\n\n" +
                       "Common areas:\n" +
                       "• Head (severe headache)\n" +
                       "• Abdomen (stomach area)\n" +
                       "• Back (upper/lower)\n" +
                       "• Joint/limb\n\n" +
                       "Rate your pain (1-10):\n" +
                       "• 7-8: Severe\n" +
                       "• 9-10: Unbearable\n\n" +
                       "How long have you had this pain?",
                "buttons": [
                    {"title": "Severe headache", "payload": "/severe_headache"},
                    {"title": "Severe abdominal", "payload": "/severe_abdominal"},
                    {"title": "Severe back pain", "payload": "/severe_back"},
                    {"title": "Other location", "payload": "/other_severe_pain"},
                    {"title": "Type my symptoms", "payload": "/type_symptoms"}
                ]
            })

        # High fever assessment
        elif "high fever" in message_lower or "/high_fever" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🌡 HIGH FEVER ASSESSMENT\n\n" +
                       "Current temperature?\n" +
                       "• 101-102°F: Moderate\n" +
                       "• 103-104°F: High\n" +
                       "• Above 104°F: Very high\n\n" +
                       "Duration:\n" +
                       "• Just started today\n" +
                       "• 1-2 days\n" +
                       "• More than 3 days\n\n" +
                       "Other symptoms:\n" +
                       "• Severe headache?\n" +
                       "• Stiff neck?\n" +
                       "• Confusion?\n" +
                       "• Rash?\n" +
                       "• Difficulty breathing?",
                "buttons": [
                    {"title": "Fever with stiff neck", "payload": "/meningitis_concern"},
                    {"title": "Above 104°F", "payload": "/very_high_fever"},
                    {"title": "Fever 3+ days", "payload": "/persistent_fever"},
                    {"title": "Fever with other symptoms", "payload": "/fever_with_symptoms"},
                    {"title": "Type my symptoms", "payload": "/type_symptoms"}
                ]
            })
            return responses

        # Urgent care info
        elif "urgent care" in message_lower or "/urgent_care" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🏥 URGENT CARE INFORMATION\n\n" +
                       "Nearest Urgent Care Centers:\n\n" +
                       "📍 MedExpress Urgent Care\n" +
                       "   123 Main St • 0.5 miles\n" +
                       "   Open until 9 PM\n\n" +
                       "📍 CityMD Urgent Care\n" +
                       "   456 Oak Ave • 1.2 miles\n" +
                       "   Open 24/7\n\n" +
                       "📍 MinuteClinic\n" +
                       "   789 Pine Rd • 2.0 miles\n" +
                       "   Open until 7 PM\n\n" +
                       "Bring: ID, insurance card, medication list",
                "buttons": [
                    {"title": "Get directions", "payload": "/directions"},
                    {"title": "Call ahead", "payload": "/call_urgent_care"}
                ]
            })

        # Additional handlers for new self-care buttons
        elif "symptom tracker" in message_lower or "/symptom_tracker" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "📊 SYMPTOM TRACKER\n\n" +
                       "Let's track your symptoms over time:\n\n" +
                       "📝 CURRENT SYMPTOMS:\n" +
                       "Rate each symptom (0-10):\n" +
                       "• Pain level: ___\n" +
                       "• Fatigue: ___\n" +
                       "• Nausea: ___\n" +
                       "• Temperature: ___°C\n\n" +
                       "⏰ TRACKING SCHEDULE:\n" +
                       "• Morning (8 AM)\n" +
                       "• Afternoon (2 PM)\n" +
                       "• Evening (8 PM)\n\n" +
                       "📈 PATTERNS TO WATCH:\n" +
                       "• Worsening symptoms\n" +
                       "• New symptoms appearing\n" +
                       "• Symptoms not improving after 48h\n\n" +
                       "💡 TIP: Keep a written log or use a health app",
                "buttons": [
                    {"title": "Log symptoms now", "payload": "/log_symptoms"},
                    {"title": "View my history", "payload": "/symptom_history"},
                    {"title": "When to worry", "payload": "/when_to_see_doctor"}
                ]
            })

        elif "headache diary" in message_lower or "/headache_diary" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "📓 HEADACHE DIARY\n\n" +
                       "Track your headaches to identify patterns:\n\n" +
                       "📝 RECORD THESE DETAILS:\n" +
                       "• Date and time started\n" +
                       "• Duration (minutes/hours)\n" +
                       "• Location (temples/forehead/back)\n" +
                       "• Type (throbbing/sharp/dull)\n" +
                       "• Severity (1-10 scale)\n\n" +
                       "🔍 POTENTIAL TRIGGERS:\n" +
                       "• Foods consumed\n" +
                       "• Sleep quality\n" +
                       "• Stress levels\n" +
                       "• Weather changes\n" +
                       "• Screen time\n" +
                       "• Menstrual cycle\n\n" +
                       "📊 AFTER 2 WEEKS:\n" +
                       "Review patterns with your GP",
                "buttons": [
                    {"title": "Start diary entry", "payload": "/log_headache"},
                    {"title": "Common triggers", "payload": "/headache_triggers"},
                    {"title": "Book GP appointment", "payload": "/schedule_appointment"}
                ]
            })

        elif "migraine check" in message_lower or "/migraine_check" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🔍 MIGRAINE ASSESSMENT\n\n" +
                       "Do you experience these symptoms?\n\n" +
                       "⚡ MIGRAINE INDICATORS:\n" +
                       "□ Moderate to severe pain\n" +
                       "□ Throbbing or pulsing sensation\n" +
                       "□ Usually one side of head\n" +
                       "□ Nausea or vomiting\n" +
                       "□ Sensitivity to light/sound\n" +
                       "□ Visual disturbances (aura)\n\n" +
                       "⏱ DURATION:\n" +
                       "□ Lasts 4-72 hours\n" +
                       "□ Worsens with physical activity\n\n" +
                       "If you checked 3+ boxes, you may have migraines.\n\n" +
                       "🏥 NEXT STEPS:\n" +
                       "• See GP for diagnosis\n" +
                       "• Consider preventive treatment\n" +
                       "• Identify personal triggers",
                "buttons": [
                    {"title": "Book GP appointment", "payload": "/schedule_appointment"},
                    {"title": "Migraine treatments", "payload": "/migraine_treatment"},
                    {"title": "Emergency signs", "payload": "/emergency_headache"}
                ]
            })

        elif "food poisoning" in message_lower or "/food_poisoning" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🦠 FOOD POISONING GUIDANCE\n\n" +
                       "⏰ TYPICAL TIMELINE:\n" +
                       "• Symptoms start: 1-72 hours after eating\n" +
                       "• Duration: 24-48 hours usually\n" +
                       "• Full recovery: 3-5 days\n\n" +
                       " IMMEDIATE CARE:\n" +
                       "• Stop eating solid food\n" +
                       "• Sip water every 15 minutes\n" +
                       "• Oral rehydration salts\n" +
                       "• Rest completely\n\n" +
                       " A&E IF:\n" +
                       "• Blood in vomit/stool\n" +
                       "• Signs of severe dehydration\n" +
                       "• High fever (>38.5°C)\n" +
                       "• Symptoms >48 hours\n" +
                       "• Confusion or dizziness\n\n" +
                       " Report to local health authority if suspect restaurant/takeaway",
                "buttons": [
                    {"title": "Dehydration signs", "payload": "/dehydration_check"},
                    {"title": "When to call 111", "payload": "/call_111"},
                    {"title": "Recovery diet", "payload": "/recovery_diet"}
                ]
            })

        elif "back exercises" in message_lower or "/back_exercises" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🤸 BACK PAIN EXERCISES\n\n" +
                       " Stop if pain worsens!\n\n" +
                       "🔄 GENTLE STRETCHES (hold 30 sec):\n\n" +
                       "1⃣ KNEE TO CHEST:\n" +
                       "• Lie on back\n" +
                       "• Pull one knee to chest\n" +
                       "• Repeat other side\n\n" +
                       "2⃣ CAT-COW STRETCH:\n" +
                       "• On hands and knees\n" +
                       "• Arch and round back slowly\n\n" +
                       "3⃣ CHILD'S POSE:\n" +
                       "• Kneel and sit back on heels\n" +
                       "• Reach arms forward\n\n" +
                       "💪 STRENGTHENING (10 reps):\n" +
                       "• Pelvic tilts\n" +
                       "• Partial crunches\n" +
                       "• Wall sits (30 seconds)\n\n" +
                       " Do 2-3 times daily",
                "buttons": [
                    {"title": "Video tutorials", "payload": "/exercise_videos"},
                    {"title": "Physiotherapy", "payload": "/physio_referral"},
                    {"title": "Pain still bad", "payload": "/persistent_back_pain"}
                ]
            })

        elif "physio referral" in message_lower or "/physio_referral" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🏥 PHYSIOTHERAPY REFERRAL\n\n" +
                       "OPTIONS FOR PHYSIOTHERAPY:\n\n" +
                       "1⃣ NHS REFERRAL:\n" +
                       "• See your GP first\n" +
                       "• Waiting time: 4-12 weeks\n" +
                       "• Free at point of care\n\n" +
                       "2⃣ SELF-REFERRAL (some areas):\n" +
                       "• Direct booking available\n" +
                       "• Check local NHS website\n" +
                       "• Usually faster access\n\n" +
                       "3⃣ PRIVATE PHYSIO:\n" +
                       "• No referral needed\n" +
                       "• Cost: £40-80 per session\n" +
                       "• Immediate availability\n\n" +
                       "📋 BRING TO FIRST APPOINTMENT:\n" +
                       "• Pain diary\n" +
                       "• List of medications\n" +
                       "• Previous scan results",
                "buttons": [
                    {"title": "Book GP for referral", "payload": "/schedule_appointment"},
                    {"title": "Find local physio", "payload": "/find_physio"},
                    {"title": "What to expect", "payload": "/physio_info"}
                ]
            })

        # Pain rating responses
        if "/pain_mild" in message or "/pain_1" in message or "/pain_2" in message or "/pain_3" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": " MILD PAIN (1-3/10)\n\n" +
                       "Good news - your pain is manageable.\n\n" +
                       "SELF-CARE RECOMMENDATIONS:\n" +
                       "• Rest the affected area\n" +
                       "• Apply ice for 20 minutes\n" +
                       "• Take OTC pain relief (as directed)\n" +
                       "• Gentle stretching\n\n" +
                       "MONITOR FOR:\n" +
                       "• Pain increasing\n" +
                       "• New symptoms\n" +
                       "• Swelling or redness\n\n" +
                       "Usually resolves in 2-3 days with care.",
                "buttons": [
                    {"title": "Pain management tips", "payload": "/pain_management"},
                    {"title": "When to see doctor", "payload": "/when_to_see_doctor"},
                    {"title": "Main menu", "payload": "/greet"}
                ]
            })

            return responses
        if "/pain_moderate" in message or "/pain_4" in message or "/pain_5" in message or "/pain_6" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": " MODERATE PAIN (4-6/10)\n\n" +
                       "This level needs attention.\n\n" +
                       "IMMEDIATE ACTIONS:\n" +
                       "• Take prescribed pain medication\n" +
                       "• Alternate ice and heat\n" +
                       "• Limit activity\n" +
                       "• Document when pain is worst\n\n" +
                       "SEE GP WITHIN 48 HOURS IF:\n" +
                       "• Not improving after 2 days\n" +
                       "• Affecting sleep\n" +
                       "• Limiting daily activities\n\n" +
                       "Consider booking an appointment.",
                "buttons": [
                    {"title": "Book GP appointment", "payload": "/schedule_appointment"},
                    {"title": "Pain relief options", "payload": "/pain_management"},
                    {"title": "Call 111 advice", "payload": "/call_111"}
                ]
            })

            return responses
        if "/pain_severe" in message or "/pain_7" in message or "/pain_8" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🔴 SEVERE PAIN (7-8/10)\n\n" +
                       "This requires medical attention TODAY.\n\n" +
                       "IMMEDIATE STEPS:\n" +
                       "1. Take maximum safe dose of pain relief\n" +
                       "2. Call GP for same-day appointment\n" +
                       "3. If unavailable, go to urgent care\n\n" +
                       "GO TO A&E IF:\n" +
                       "• Sudden onset severe pain\n" +
                       "• With fever or vomiting\n" +
                       "• After injury or fall\n" +
                       "• Chest, abdomen or head pain\n\n" +
                       "Don't wait if pain is unbearable.",
                "buttons": [
                    {"title": "Book urgent appointment", "payload": "/urgent_appointment"},
                    {"title": "Find urgent care", "payload": "/urgent_care"},
                    {"title": "Call 111 now", "payload": "/call_111"}
                ]
            })

            return responses
        if "/pain_extreme" in message or "/pain_9" in message or "/pain_10" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": " EXTREME PAIN (9-10/10)\n\n" +
                       " SEEK EMERGENCY CARE NOW\n\n" +
                       "This level of pain is a medical emergency.\n\n" +
                       "CALL 999 IF:\n" +
                       "• Unbearable pain\n" +
                       "• Can't move or function\n" +
                       "• Suspected broken bone\n" +
                       "• Severe injury\n\n" +
                       "GO TO A&E IMMEDIATELY IF:\n" +
                       "• Severe abdominal pain\n" +
                       "• Chest pain\n" +
                       "• Head injury pain\n\n" +
                       "Don't drive yourself - call ambulance.",
                "buttons": [
                    {"title": "Call 999", "payload": "/call_999"},
                    {"title": "Go to A&E", "payload": "/go_to_ae"},
                    {"title": "Call 111 for advice", "payload": "/call_111"}
                ]
            })

            return responses
        # Emergency help direct from button
        if "/emergency_help" in message or "/emergency" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": " EMERGENCY GUIDANCE\n\n" +
                       " CALL 999 IMMEDIATELY IF:\n\n" +
                       "🔴 Life-threatening symptoms:\n" +
                       "• Chest pain or pressure\n" +
                       "• Difficulty breathing\n" +
                       "• Severe bleeding\n" +
                       "• Loss of consciousness\n" +
                       "• Stroke symptoms (FAST)\n" +
                       "• Severe allergic reaction\n\n" +
                       " WHAT TO DO:\n" +
                       "1. Call 999 now\n" +
                       "2. Stay calm\n" +
                       "3. Follow operator instructions\n" +
                       "4. Don't hang up\n\n" +
                       "🏥 IF LESS URGENT:\n" +
                       "Call 111 for urgent medical advice\n\n" +
                       "Is this a life-threatening emergency?",
                "buttons": [
                    {"title": "Yes - Call 999", "payload": "/call_999"},
                    {"title": "No - Describe symptoms", "payload": "/describe_symptoms"},
                    {"title": "Call 111 for advice", "payload": "/call_111"},
                    {"title": "Main menu", "payload": "/greet"}
                ]
            })

            return responses
        # When to see doctor
        elif "when to see" in message_lower or "/when_to_see_doctor" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🩺 WHEN TO SEE A DOCTOR\n\n" +
                       "See doctor TODAY if:\n" +
                       "• Fever > 103°F\n" +
                       "• Severe pain (7-10/10)\n" +
                       "• Difficulty breathing\n" +
                       "• Persistent vomiting\n" +
                       "• Signs of infection\n\n" +
                       "Within 24-48 hours if:\n" +
                       "• Symptoms worsen\n" +
                       "• No improvement after 3 days\n" +
                       "• Moderate pain (4-6/10)\n" +
                       "• Recurring symptoms\n\n" +
                       "Emergency room if:\n" +
                       "• Chest pain\n" +
                       "• Stroke symptoms\n" +
                       "• Severe bleeding\n" +
                       "• Loss of consciousness",
                "buttons": [
                    {"title": "Book appointment", "payload": "/schedule_appointment"},
                    {"title": "Emergency help", "payload": "/emergency_help"}
                ]
            })

        # Free text symptom analysis - Check BEFORE greeting
        # Check for any symptom keywords in free text
        symptom_found = False

        # Common symptom patterns
        pain_words = ["pain", "ache", "hurt", "sore", "painful", "hurting"]
        respiratory_words = ["breath", "breathing", "wheeze", "cough", "congestion"]
        gi_words = ["nausea", "vomit", "diarrhea", "constipation", "bloat", "gas"]
        neuro_words = ["dizzy", "faint", "confused", "memory", "numbness", "tingling"]
        skin_words = ["rash", "itch", "hives", "swelling", "bump", "spot"]
        general_words = ["tired", "fatigue", "weak", "fever", "chills", "sweat"]

        # Analyze free text for symptoms
        if any(word in message_lower for word in pain_words):
            # Check if back pain specifically mentioned
            if "back" in message_lower:
                responses.append({
                    "recipient_id": sender_id,
                    "text": "🔙 BACK PAIN ASSESSMENT\n\n" +
                           "I understand you have back pain. Let me help assess this.\n\n" +
                           "Location of pain:\n" +
                           "• Upper back (between shoulders)\n" +
                           "• Mid back\n" +
                           "• Lower back (most common)\n" +
                           "• Radiating to legs\n\n" +
                           "How severe (1-10)?\n" +
                           "When did it start?\n" +
                           "Any recent injury or strain?",
                    "buttons": [
                        {"title": "Mild (1-3) manageable", "payload": "/mild_back_pain"},
                        {"title": "Moderate (4-6) limiting", "payload": "/moderate_back_pain"},
                        {"title": "Severe (7-10) debilitating", "payload": "/severe_back"},
                        {"title": "With numbness/tingling", "payload": "/back_with_neuro"},
                        {"title": "Type my symptoms", "payload": "/type_symptoms"}
                    ]
                })
            else:
                responses.append({
                    "recipient_id": sender_id,
                    "text": "📍 I see you're experiencing pain.\n\n" +
                           "To help you better, please tell me:\n\n" +
                           "1. WHERE is the pain located?\n" +
                           "2. HOW SEVERE is it (1-10)?\n" +
                           "3. WHEN did it start?\n" +
                           "4. WHAT TYPE of pain?\n" +
                           "   • Sharp/stabbing\n" +
                           "   • Dull/aching\n" +
                           "   • Burning\n" +
                           "   • Throbbing\n\n" +
                           "Select the area that best matches:",
                    "buttons": [
                        {"title": "Head/neck pain", "payload": "/headache"},
                        {"title": "Chest pain", "payload": "/chest_pain"},
                        {"title": "Abdominal pain", "payload": "/stomach"},
                        {"title": "Back pain", "payload": "/back_pain"},
                        {"title": "Other location", "payload": "/other_pain"},
                        {"title": "Type my symptoms", "payload": "/type_symptoms"}
                    ]
                })
            symptom_found = True

        elif any(word in message_lower for word in respiratory_words):
            responses.append({
                "recipient_id": sender_id,
                "text": "🫁 I see you have breathing/respiratory concerns.\n\n" +
                       "How severe is your symptom?",
                "buttons": [
                    {"title": "Mild - manageable", "payload": "/mild_cold_flu"},
                    {"title": "Moderate - concerning", "payload": "/moderate_breathing"},
                    {"title": "Severe - struggling", "payload": "/breathing_difficulty"},
                    {"title": "Emergency - can't breathe", "payload": "/emergency_breathing"},
                    {"title": "Type my symptoms", "payload": "/type_symptoms"}
                ]
            })
            symptom_found = True

        elif any(word in message_lower for word in gi_words):
            responses.append({
                "recipient_id": sender_id,
                "text": "🤢 I see you have digestive symptoms.\n\n" +
                       "What are you experiencing?",
                "buttons": [
                    {"title": "Nausea/vomiting", "payload": "/nausea_vomiting"},
                    {"title": "Diarrhea", "payload": "/diarrhea"},
                    {"title": "Constipation", "payload": "/constipation"},
                    {"title": "Stomach pain", "payload": "/stomach"},
                    {"title": "Multiple GI issues", "payload": "/mild_digestive"},
                    {"title": "Type my symptoms", "payload": "/type_symptoms"}
                ]
            })
            symptom_found = True

        elif any(word in message_lower for word in general_words):
            # Check specifically for fatigue/tired
            if "tired" in message_lower or "fatigue" in message_lower:
                responses.append({
                    "recipient_id": sender_id,
                    "text": "😴 FATIGUE ASSESSMENT\n\n" +
                           "I see you're feeling tired. Let me help assess this.\n\n" +
                           "How long have you been feeling fatigued?\n" +
                           "• Just today\n" +
                           "• Few days\n" +
                           "• More than a week\n" +
                           "• Chronic (months)\n\n" +
                           "Is it accompanied by:",
                    "buttons": [
                        {"title": "Just tired, no other symptoms", "payload": "/mild_fatigue"},
                        {"title": "With body aches", "payload": "/fatigue_with_aches"},
                        {"title": "With fever", "payload": "/fatigue_with_fever"},
                        {"title": "With other symptoms", "payload": "/moderate_multiple"},
                        {"title": "Type my symptoms", "payload": "/type_symptoms"}
                    ]
                })
            else:
                responses.append({
                    "recipient_id": sender_id,
                    "text": "🌡 I understand you're not feeling well.\n\n" +
                           "How severe are your symptoms overall?",
                    "buttons": [
                        {"title": "Mild - can manage", "payload": "/mild_symptoms"},
                        {"title": "Moderate - need help", "payload": "/moderate_symptoms"},
                        {"title": "Severe - very unwell", "payload": "/severe_symptoms"},
                        {"title": "Not sure", "payload": "/describe_symptoms"},
                        {"title": "Type my symptoms", "payload": "/type_symptoms"}
                    ]
                })
            symptom_found = True

        # Energy boosting tips
        if "/energy_tips" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "⚡ ENERGY BOOSTING TIPS\n\n" +
                       "IMMEDIATE ENERGY BOOST:\n" +
                       "• Take a 5-minute walk\n" +
                       "• Drink a glass of cold water\n" +
                       "• Do 10 jumping jacks\n" +
                       "• Eat a healthy snack\n\n" +
                       "NUTRITION FOR ENERGY:\n" +
                       "• Complex carbs (oatmeal, whole grains)\n" +
                       "• Protein (nuts, eggs, yogurt)\n" +
                       "• Iron-rich foods (spinach, beans)\n" +
                       "• B vitamins (bananas, avocados)\n\n" +
                       "LIFESTYLE CHANGES:\n" +
                       "• Sleep 7-9 hours nightly\n" +
                       "• Exercise 30 min daily\n" +
                       "• Limit caffeine after 2pm\n" +
                       "• Stay hydrated\n\n" +
                       "AVOID ENERGY DRAINS:\n" +
                       "• Skipping meals\n" +
                       "• Too much sugar\n" +
                       "• Dehydration\n" +
                       "• Excessive screen time",
                "buttons": [
                    {"title": "Sleep improvement", "payload": "/sleep_tips"},
                    {"title": "Fatigue assessment", "payload": "/mild_fatigue"},
                    {"title": "Book GP appointment", "payload": "/schedule_appointment"}
                ]
            })

            return responses
        # Sleep tips
        if "/sleep_tips" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "😴 SLEEP HYGIENE TIPS\n\n" +
                       "BEDTIME ROUTINE:\n" +
                       "• Same sleep/wake time daily\n" +
                       "• Wind down 1 hour before bed\n" +
                       "• No screens 30 min before sleep\n" +
                       "• Keep bedroom cool (65-68°F)\n\n" +
                       "IMPROVE SLEEP QUALITY:\n" +
                       "• Dark, quiet room\n" +
                       "• Comfortable mattress/pillows\n" +
                       "• White noise if needed\n\n" +
                       "DAYTIME HABITS:\n" +
                       "• Morning sunlight exposure\n" +
                       "• Exercise (not late evening)\n" +
                       "• Limit naps to 20 min\n" +
                       "• No caffeine after 2pm",
                "buttons": [
                    {"title": "Relaxation techniques", "payload": "/relaxation"},
                    {"title": "When to see doctor", "payload": "/when_to_see_doctor"},
                    {"title": "Main menu", "payload": "/greet"}
                ]
            })

            return responses
        # Call 999/911 emergency
        if "/call_999" in message or "/call_911" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": " CALLING EMERGENCY SERVICES\n\n" +
                       " DIAL 999 (UK) or 911 (US) NOW\n\n" +
                       "TELL THE OPERATOR:\n" +
                       "1. Your exact location/address\n" +
                       "2. Main symptom (e.g., 'chest pain')\n" +
                       "3. Patient's age\n" +
                       "4. Consciousness level\n" +
                       "5. Breathing status\n\n" +
                       "WHILE WAITING:\n" +
                       "• Stay calm\n" +
                       "• Don't hang up\n" +
                       "• Follow operator instructions\n" +
                       "• Unlock door if possible\n" +
                       "• Gather medications list",
                "buttons": [
                    {"title": "I called 999", "payload": "/called_911"},
                    {"title": "First aid guidance", "payload": "/first_aid"}
                ]
            })

            return responses
        # View appointments
        if "/view_appointments" in message:
            if sender_id in self.appointments:
                apt = self.appointments[sender_id]
                responses.append({
                    "recipient_id": sender_id,
                    "text": f" YOUR APPOINTMENTS\n\n" +
                           f"Upcoming appointment:\n" +
                           f"• Date: {apt.get('date', 'Not set')}\n" +
                           f"• Time: {apt.get('time', 'Not set')}\n" +
                           f"• Doctor: {apt.get('doctor', 'Not assigned')}\n" +
                           f"• Confirmation: {apt.get('confirmation', 'Pending')}\n\n" +
                           f"Please arrive 15 minutes early.",
                    "buttons": [
                        {"title": "Cancel appointment", "payload": "/cancel_appointment"},
                        {"title": "Reschedule", "payload": "/schedule_appointment"},
                        {"title": "Main menu", "payload": "/greet"}
                    ]
                })
            else:
                responses.append({
                    "recipient_id": sender_id,
                    "text": " NO APPOINTMENTS FOUND\n\n" +
                           "You don't have any scheduled appointments.",
                    "buttons": [
                        {"title": "Schedule appointment", "payload": "/schedule_appointment"},
                        {"title": "Main menu", "payload": "/greet"}
                    ]
                })

            return responses
        # Nurse assessment - ONLY payload
        if message.strip() == "/nurse":
            responses.append({
                "recipient_id": sender_id,
                "text": "NURSE TRIAGE ASSESSMENT\n\n" +
                       "I'll connect you with a nurse for assessment.\n\n" +
                       "OPTIONS:\n" +
                       " Call 111 (24/7 NHS nurse)\n" +
                       " Online nurse chat\n" +
                       " Video consultation\n\n" +
                       "Average wait: 5-10 minutes",
                "buttons": [
                    {"title": "Call 111 now", "payload": "/call_111"},
                    {"title": "Describe symptoms", "payload": "/describe_symptoms"},
                    {"title": "Main menu", "payload": "/greet"}
                ]
            })

            return responses
        # Severe headache
        if "/severe_headache" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🤕 SEVERE HEADACHE ASSESSMENT\n\n" +
                       " CALL 999 IF:\n" +
                       "• Sudden 'thunderclap' headache\n" +
                       "• With fever and stiff neck\n" +
                       "• After head injury\n" +
                       "• With confusion/vision loss\n\n" +
                       "Is this an emergency headache?",
                "buttons": [
                    {"title": "Yes - Emergency", "payload": "/call_999"},
                    {"title": "No - Still severe", "payload": "/headache_severe_care"},
                    {"title": "Migraine history", "payload": "/migraine_check"}
                ]
            })

            return responses
        # Hydration tips
        if "/hydration_tips" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "💧 HYDRATION GUIDE\n\n" +
                       "DAILY WATER INTAKE:\n" +
                       "• Men: 3.7 liters (15.5 cups)\n" +
                       "• Women: 2.7 liters (11.5 cups)\n" +
                       "• More if exercising/hot weather\n\n" +
                       "SIGNS OF DEHYDRATION:\n" +
                       "• Dark yellow urine\n" +
                       "• Headache\n" +
                       "• Fatigue\n" +
                       "• Dry mouth/lips\n" +
                       "• Dizziness",
                "buttons": [
                    {"title": "Dehydration check", "payload": "/dehydration_check"},
                    {"title": "Main menu", "payload": "/greet"}
                ]
            })

            return responses
        # Breathing exercises
        if "/breathing_exercises" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🫁 BREATHING EXERCISES\n\n" +
                       "CALM BREATHING (4-7-8):\n" +
                       "1. Exhale completely\n" +
                       "2. Inhale through nose - 4 counts\n" +
                       "3. Hold breath - 7 counts\n" +
                       "4. Exhale through mouth - 8 counts\n" +
                       "5. Repeat 3-4 times\n\n" +
                       "BENEFITS:\n" +
                       "✓ Reduces anxiety\n" +
                       "✓ Lowers blood pressure\n" +
                       "✓ Improves focus",
                "buttons": [
                    {"title": "Relaxation techniques", "payload": "/relaxation"},
                    {"title": "Main menu", "payload": "/greet"}
                ]
            })

            return responses
        # Relaxation techniques
        if "/relaxation" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🧘 RELAXATION TECHNIQUES\n\n" +
                       "QUICK TECHNIQUES:\n" +
                       "• Deep breathing (5 min)\n" +
                       "• Visualization (imagine calm place)\n" +
                       "• Body scan meditation\n" +
                       "• Gentle stretching\n\n" +
                       "DAILY PRACTICE:\n" +
                       "• Morning: 5 min breathing\n" +
                       "• Lunch: Quick stretch\n" +
                       "• Evening: Full relaxation",
                "buttons": [
                    {"title": "Breathing exercises", "payload": "/breathing_exercises"},
                    {"title": "Sleep better", "payload": "/sleep_tips"},
                    {"title": "Main menu", "payload": "/greet"}
                ]
            })

            return responses
        # Mild cold/flu
        if "/mild_cold_flu" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🤧 COLD/FLU CARE\n\n" +
                       "SYMPTOM RELIEF:\n" +
                       "• Rest - most important\n" +
                       "• Fluids - 2-3L daily\n" +
                       "• Paracetamol for fever/aches\n" +
                       "• Throat lozenges\n\n" +
                       "HOME REMEDIES:\n" +
                       "• Honey & lemon tea\n" +
                       "• Steam inhalation\n" +
                       "• Warm salt water gargle\n\n" +
                       "SEE DOCTOR IF:\n" +
                       "• Symptoms >10 days\n" +
                       "• Getting worse\n" +
                       "• Breathing difficulties",
                "buttons": [
                    {"title": "Self-care guide", "payload": "/self_care_cold"},
                    {"title": "When to worry", "payload": "/when_to_see_doctor"},
                    {"title": "Main menu", "payload": "/greet"}
                ]
            })

            return responses
        # Severe abdominal pain
        if "/severe_abdominal" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🔴 SEVERE ABDOMINAL PAIN\n\n" +
                       " SEEK EMERGENCY CARE IF:\n" +
                       "• Sudden, severe pain\n" +
                       "• Pain with fever\n" +
                       "• Vomiting blood\n" +
                       "• Black/bloody stools\n" +
                       "• Rigid/hard abdomen\n\n" +
                       "How severe is your pain?",
                "buttons": [
                    {"title": "Unbearable - Call 999", "payload": "/call_999"},
                    {"title": "Severe but stable", "payload": "/urgent_care"},
                    {"title": "With other symptoms", "payload": "/abdominal_symptoms"}
                ]
            })

            return responses
        # Add to calendar
        if "/add_to_calendar" in message:
            if sender_id in self.appointments:
                apt = self.appointments[sender_id]
                responses.append({
                    "recipient_id": sender_id,
                    "text": " ADD TO CALENDAR\n\n" +
                           f"Copy these details:\n\n" +
                           f"Event: Medical Appointment\n" +
                           f"Date: {apt.get('date', 'TBD')}\n" +
                           f"Time: {apt.get('time', 'TBD')}\n" +
                           f"Doctor: {apt.get('doctor', 'TBD')}\n\n" +
                           "SET REMINDERS:\n" +
                           "• 1 day before\n" +
                           "• 2 hours before",
                    "buttons": [
                        {"title": "View appointment", "payload": "/view_appointments"},
                        {"title": "Main menu", "payload": "/greet"}
                    ]
                })


            return responses
        # Called 911/999
        if "/called_911" in message or "/called_999" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": " HELP IS ON THE WAY\n\n" +
                       "Average arrival: 7-10 minutes\n\n" +
                       "WHILE WAITING:\n" +
                       "• Keep patient calm\n" +
                       "• Monitor breathing\n" +
                       "• Note any changes\n" +
                       "• Gather medications\n" +
                       "• Unlock front door\n\n" +
                       "Stay on line with 999 if requested.",
                "buttons": [
                    {"title": "First aid tips", "payload": "/first_aid"},
                    {"title": "What to tell paramedics", "payload": "/paramedic_info"}
                ]
            })

            return responses
        # Go to A&E
        if "/go_to_ae" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🏥 A&E DEPARTMENTS\n\n" +
                       "NEAREST A&E:\n" +
                       "📍 City General Hospital\n" +
                       "   24/7 Emergency Department\n" +
                       "   Average wait: 2-4 hours\n\n" +
                       "BRING WITH YOU:\n" +
                       "• Photo ID\n" +
                       "• List of medications\n" +
                       "• Insurance details\n" +
                       "• Phone charger\n\n" +
                       " Call 999 if you can't get there safely",
                "buttons": [
                    {"title": "Get directions", "payload": "/directions"},
                    {"title": "Call 999 instead", "payload": "/call_999"}
                ]
            })

            return responses
        # More handlers for all missing payloads
        if "/urgent_appointment" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": " URGENT APPOINTMENT\n\n" +
                       "For same-day urgent care:\n\n" +
                       " CALL YOUR GP NOW\n" +
                       "Say it's urgent - they keep slots\n\n" +
                       "ALTERNATIVES:\n" +
                       "• Walk-in centres\n" +
                       "• Urgent care clinics\n" +
                       "• 111 service\n\n" +
                       "If can't wait: Go to A&E",
                "buttons": [
                    {"title": "Find urgent care", "payload": "/urgent_care"},
                    {"title": "Call 111", "payload": "/call_111"},
                    {"title": "Go to A&E", "payload": "/go_to_ae"}
                ]
            })

            return responses
        if "/dehydration_check" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "💧 DEHYDRATION CHECK\n\n" +
                       "MILD SIGNS:\n" +
                       "• Thirst\n" +
                       "• Dry mouth\n" +
                       "• Dark yellow urine\n" +
                       "• Tiredness\n\n" +
                       "SEVERE SIGNS:\n" +
                       "• Dizziness\n" +
                       "• Rapid heartbeat\n" +
                       "• Sunken eyes\n" +
                       "• No urination 8+ hours\n\n" +
                       "Treatment: Sip water slowly",
                "buttons": [
                    {"title": "Hydration tips", "payload": "/hydration_tips"},
                    {"title": "When to worry", "payload": "/when_to_see_doctor"}
                ]
            })

            return responses
        if "/mild_headache" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "😌 MILD HEADACHE RELIEF\n\n" +
                       "IMMEDIATE RELIEF:\n" +
                       "• Paracetamol or ibuprofen\n" +
                       "• Drink water\n" +
                       "• Rest in quiet room\n" +
                       "• Apply cold compress\n\n" +
                       "Usually resolves within hours",
                "buttons": [
                    {"title": "Headache diary", "payload": "/headache_diary"},
                    {"title": "Relaxation", "payload": "/relaxation"},
                    {"title": "Main menu", "payload": "/greet"}
                ]
            })

            return responses
        if "/mild_digestive" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🤢 DIGESTIVE UPSET CARE\n\n" +
                       "IMMEDIATE RELIEF:\n" +
                       "• Small sips of water\n" +
                       "• Avoid solid food initially\n" +
                       "• Rest upright\n" +
                       "• Peppermint tea\n\n" +
                       "Start with bland foods when ready",
                "buttons": [
                    {"title": "Food poisoning info", "payload": "/food_poisoning"},
                    {"title": "When to worry", "payload": "/when_to_see_doctor"},
                    {"title": "Main menu", "payload": "/greet"}
                ]
            })

            return responses
        if "/moderate_infection" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🦠 INFECTION MANAGEMENT\n\n" +
                       "SIGNS:\n" +
                       "• Fever\n" +
                       "• Redness/swelling\n" +
                       "• Pus\n" +
                       "• Increasing pain\n\n" +
                       "See GP today if spreading",
                "buttons": [
                    {"title": "Book urgent appointment", "payload": "/urgent_appointment"},
                    {"title": "Call 111", "payload": "/call_111"}
                ]
            })

            return responses
        # Back pain handlers
        if "/mild_back_pain" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "💚 MILD BACK PAIN RELIEF\n\n" +
                       "IMMEDIATE STEPS:\n" +
                       "• Keep moving gently\n" +
                       "• Apply heat or ice\n" +
                       "• Over-counter painkillers\n" +
                       "• Gentle stretches\n\n" +
                       "Usually improves in few days",
                "buttons": [
                    {"title": "Back exercises", "payload": "/back_exercises"},
                    {"title": "When to worry", "payload": "/when_to_see_doctor"},
                    {"title": "Main menu", "payload": "/greet"}
                ]
            })

            return responses
        if "/moderate_back_pain" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": " MODERATE BACK PAIN\n\n" +
                       "MANAGEMENT:\n" +
                       "• Regular painkillers\n" +
                       "• Alternate heat/ice\n" +
                       "• Gentle movement\n" +
                       "• Avoid heavy lifting\n\n" +
                       "SEE GP IF:\n" +
                       "• Pain >1 week\n" +
                       "• Getting worse\n" +
                       "• Numbness/tingling",
                "buttons": [
                    {"title": "Book appointment", "payload": "/schedule_appointment"},
                    {"title": "Physiotherapy", "payload": "/physio_referral"},
                    {"title": "Pain management", "payload": "/pain_management"}
                ]
            })

            return responses
        if "/severe_back" in message or "/back_with_neuro" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🔴 SEVERE BACK PAIN WARNING\n\n" +
                       " SEEK URGENT CARE IF:\n" +
                       "• Loss of bladder/bowel control\n" +
                       "• Leg weakness\n" +
                       "• Numbness in groin\n" +
                       "• Can't walk\n\n" +
                       "These are RED FLAGS - A&E NOW",
                "buttons": [
                    {"title": "Go to A&E", "payload": "/go_to_ae"},
                    {"title": "Call 999", "payload": "/call_999"},
                    {"title": "Urgent GP", "payload": "/urgent_appointment"}
                ]
            })

            return responses
        # Digestive symptoms
        if "/nausea_vomiting" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🤮 NAUSEA & VOMITING CARE\n\n" +
                       "IMMEDIATE HELP:\n" +
                       "• Small sips of water\n" +
                       "• Ginger tea\n" +
                       "• Fresh air\n" +
                       "• Sit upright\n\n" +
                       " SEEK HELP IF:\n" +
                       "• Blood in vomit\n" +
                       "• Can't keep fluids down 24h\n" +
                       "• Signs of dehydration",
                "buttons": [
                    {"title": "Dehydration check", "payload": "/dehydration_check"},
                    {"title": "When to worry", "payload": "/when_to_see_doctor"},
                    {"title": "Main menu", "payload": "/greet"}
                ]
            })

            return responses
        if "/diarrhea" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "💩 DIARRHEA MANAGEMENT\n\n" +
                       "IMMEDIATE CARE:\n" +
                       "• Oral rehydration salts\n" +
                       "• Clear fluids frequently\n" +
                       "• Avoid dairy products\n" +
                       "• Rest\n\n" +
                       " SEE DOCTOR IF:\n" +
                       "• Blood in stool\n" +
                       "• High fever\n" +
                       "• Lasts >3 days",
                "buttons": [
                    {"title": "Hydration tips", "payload": "/hydration_tips"},
                    {"title": "Food poisoning", "payload": "/food_poisoning"},
                    {"title": "When to worry", "payload": "/when_to_see_doctor"}
                ]
            })

            return responses
        if "/constipation" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🚽 CONSTIPATION RELIEF\n\n" +
                       "IMMEDIATE HELP:\n" +
                       "• Drink warm water\n" +
                       "• Gentle exercise\n" +
                       "• Abdominal massage\n" +
                       "• Prune juice\n\n" +
                       "DIETARY CHANGES:\n" +
                       "• More fiber\n" +
                       "• 8+ glasses water daily",
                "buttons": [
                    {"title": "Dietary advice", "payload": "/diet_fiber"},
                    {"title": "When to worry", "payload": "/when_to_see_doctor"},
                    {"title": "Main menu", "payload": "/greet"}
                ]
            })

            return responses
        # Abdominal pain types
        if "/stomach" in message or "/abdominal_symptoms" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🤒 STOMACH PAIN ASSESSMENT\n\n" +
                       "LOCATION HELPS DIAGNOSIS:\n" +
                       "• Upper right: Gallbladder\n" +
                       "• Upper center: Stomach\n" +
                       "• Around navel: Small intestine\n" +
                       "• Lower right: Appendix\n\n" +
                       "DESCRIBE YOUR PAIN:",
                "buttons": [
                    {"title": "Sharp/stabbing", "payload": "/sharp_abdominal"},
                    {"title": "Cramping", "payload": "/cramping_abdominal"},
                    {"title": "Burning", "payload": "/burning_abdominal"},
                    {"title": "Constant ache", "payload": "/aching_abdominal"}
                ]
            })

            return responses
        if "/sharp_abdominal" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🔪 SHARP ABDOMINAL PAIN\n\n" +
                       "This could be serious.\n\n" +
                       "POSSIBLE CAUSES:\n" +
                       "• Appendicitis\n" +
                       "• Gallstones\n" +
                       "• Kidney stones\n\n" +
                       "Seek urgent care if severe",
                "buttons": [
                    {"title": "Go to A&E", "payload": "/go_to_ae"},
                    {"title": "Call 111", "payload": "/call_111"},
                    {"title": "See more symptoms", "payload": "/abdominal_symptoms"}
                ]
            })

            return responses
        if "/cramping_abdominal" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "〰 CRAMPING PAIN\n\n" +
                       "COMMON CAUSES:\n" +
                       "• IBS\n" +
                       "• Gas/bloating\n" +
                       "• Food intolerance\n" +
                       "• Period cramps\n\n" +
                       "Usually not serious but monitor",
                "buttons": [
                    {"title": "Self-care tips", "payload": "/digestive_self_care"},
                    {"title": "When to worry", "payload": "/when_to_see_doctor"},
                    {"title": "Main menu", "payload": "/greet"}
                ]
            })

            return responses
        if "/burning_abdominal" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🔥 BURNING PAIN\n\n" +
                       "LIKELY CAUSES:\n" +
                       "• Heartburn/GERD\n" +
                       "• Stomach ulcer\n" +
                       "• Gastritis\n\n" +
                       "Try antacids for relief",
                "buttons": [
                    {"title": "Heartburn relief", "payload": "/heartburn_relief"},
                    {"title": "Diet advice", "payload": "/diet_advice"},
                    {"title": "Book GP", "payload": "/schedule_appointment"}
                ]
            })

            return responses
        if "/aching_abdominal" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "😣 CONSTANT ACHE\n\n" +
                       "POSSIBLE CAUSES:\n" +
                       "• Constipation\n" +
                       "• Viral infection\n" +
                       "• Stress\n\n" +
                       "Monitor for changes",
                "buttons": [
                    {"title": "Track symptoms", "payload": "/symptom_diary"},
                    {"title": "Self-care", "payload": "/self_care"},
                    {"title": "Main menu", "payload": "/greet"}
                ]
            })

            return responses
        # Other pain locations
        if "/other_pain" in message or "/other_severe_pain" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "📍 OTHER PAIN LOCATION\n\n" +
                       "Please describe:\n" +
                       "• Where is the pain?\n" +
                       "• How long have you had it?\n" +
                       "• Rate severity (1-10)\n\n" +
                       "Common areas we can help with:",
                "buttons": [
                    {"title": "Joint pain", "payload": "/joint_pain"},
                    {"title": "Muscle pain", "payload": "/muscle_pain"},
                    {"title": "Nerve pain", "payload": "/nerve_pain"},
                    {"title": "Type symptoms", "payload": "/type_symptoms"}
                ]
            })

            return responses
        if "/joint_pain" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🦴 JOINT PAIN ASSESSMENT\n\n" +
                       "SYMPTOMS TO WATCH:\n" +
                       "• Swelling\n" +
                       "• Redness\n" +
                       "• Warmth\n" +
                       "• Stiffness\n\n" +
                       "Could be arthritis, injury, or infection",
                "buttons": [
                    {"title": "Self-care", "payload": "/joint_care"},
                    {"title": "Book GP", "payload": "/schedule_appointment"},
                    {"title": "When urgent", "payload": "/when_to_see_doctor"}
                ]
            })

            return responses
        if "/muscle_pain" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "💪 MUSCLE PAIN CARE\n\n" +
                       "RICE METHOD:\n" +
                       "• Rest\n" +
                       "• Ice (first 48h)\n" +
                       "• Compression\n" +
                       "• Elevation\n\n" +
                       "Usually improves in few days",
                "buttons": [
                    {"title": "Stretches", "payload": "/muscle_stretches"},
                    {"title": "Pain relief", "payload": "/pain_management"},
                    {"title": "Main menu", "payload": "/greet"}
                ]
            })

            return responses
        if "/nerve_pain" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "⚡ NERVE PAIN\n\n" +
                       "CHARACTERISTICS:\n" +
                       "• Shooting/burning\n" +
                       "• Numbness\n" +
                       "• Tingling\n" +
                       "• Weakness\n\n" +
                       "Often needs medical assessment",
                "buttons": [
                    {"title": "Book GP urgently", "payload": "/urgent_appointment"},
                    {"title": "Pain management", "payload": "/pain_management"},
                    {"title": "Call 111", "payload": "/call_111"}
                ]
            })

            return responses
        # Telemedicine
        if "/telemedicine" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "💻 VIDEO CONSULTATION\n\n" +
                       "AVAILABLE SERVICES:\n" +
                       "• NHS Video Consults\n" +
                       "• Private GP services\n" +
                       "• Specialist referrals\n\n" +
                       "Average wait: 30 minutes",
                "buttons": [
                    {"title": "Book video consult", "payload": "/book_video"},
                    {"title": "Call 111 instead", "payload": "/call_111"},
                    {"title": "Main menu", "payload": "/greet"}
                ]
            })

            return responses
        # Symptom diary
        if "/symptom_diary" in message or "/log_symptoms" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "📝 SYMPTOM DIARY\n\n" +
                       "TRACK DAILY:\n" +
                       "• Time symptoms occur\n" +
                       "• Severity (1-10 scale)\n" +
                       "• Duration\n" +
                       "• Triggers\n" +
                       "• What helped\n\n" +
                       "Keep for at least 2 weeks",
                "buttons": [
                    {"title": "Start logging", "payload": "/start_diary"},
                    {"title": "View tips", "payload": "/diary_tips"},
                    {"title": "Main menu", "payload": "/greet"}
                ]
            })

            return responses
        # First aid
        if "/first_aid" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🚑 FIRST AID BASICS\n\n" +
                       "CHECK FOR:\n" +
                       "• Danger\n" +
                       "• Response\n" +
                       "• Airway\n" +
                       "• Breathing\n" +
                       "• Circulation\n\n" +
                       "What's the emergency?",
                "buttons": [
                    {"title": "Not breathing", "payload": "/cpr_guide"},
                    {"title": "Bleeding", "payload": "/bleeding_control"},
                    {"title": "Choking", "payload": "/choking_help"},
                    {"title": "Burns", "payload": "/burn_care"}
                ]
            })

            return responses
        # Food poisoning
        if "/food_poisoning" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🤠 FOOD POISONING\n\n" +
                       "SYMPTOMS:\n" +
                       "• Nausea/vomiting\n" +
                       "• Diarrhea\n" +
                       "• Stomach cramps\n" +
                       "• Fever\n\n" +
                       "RECOVERY:\n" +
                       "• Rest\n" +
                       "• Stay hydrated\n" +
                       "• BRAT diet when ready",
                "buttons": [
                    {"title": "Hydration guide", "payload": "/hydration_tips"},
                    {"title": "When to worry", "payload": "/when_to_see_doctor"},
                    {"title": "Main menu", "payload": "/greet"}
                ]
            })

            return responses
        # When to see doctor
        if "/when_to_see_doctor" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "👨‍⛕ SEE A DOCTOR IF:\n\n" +
                       "• Symptoms persist >1 week\n" +
                       "• Getting worse\n" +
                       "• Fever >39°C\n" +
                       "• Unexplained weight loss\n" +
                       "• Blood in urine/stool\n" +
                       "• Persistent pain\n" +
                       "• Breathing difficulties\n\n" +
                       "Trust your instincts",
                "buttons": [
                    {"title": "Book appointment", "payload": "/schedule_appointment"},
                    {"title": "Call 111", "payload": "/call_111"},
                    {"title": "Main menu", "payload": "/greet"}
                ]
            })

            return responses
        # Headache diary
        if "/headache_diary" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "📓 HEADACHE DIARY\n\n" +
                       "TRACK:\n" +
                       "• Date/time\n" +
                       "• Location of pain\n" +
                       "• Severity (1-10)\n" +
                       "• Triggers\n" +
                       "• What helped\n\n" +
                       "Share with your GP",
                "buttons": [
                    {"title": "Start tracking", "payload": "/start_diary"},
                    {"title": "Headache types", "payload": "/headache_types"},
                    {"title": "Main menu", "payload": "/greet"}
                ]
            })

            return responses
        # Paramedic info
        if "/paramedic_info" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🚑 WHAT TO TELL PARAMEDICS\n\n" +
                       "KEY INFORMATION:\n" +
                       "• Main symptoms\n" +
                       "• When it started\n" +
                       "• Medical conditions\n" +
                       "• Current medications\n" +
                       "• Allergies\n" +
                       "• Last food/drink\n\n" +
                       "Have medications ready to show",
                "buttons": [
                    {"title": "Emergency checklist", "payload": "/emergency_checklist"},
                    {"title": "Main menu", "payload": "/greet"}
                ]
            })

            return responses
        # Directions to A&E
        if "/directions" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "📏 NEAREST A&E\n\n" +
                       "City General Hospital\n" +
                       "123 Hospital Road\n" +
                       "Open 24/7\n\n" +
                       "BY CAR: 15 minutes\n" +
                       "BY BUS: Routes 12, 45\n" +
                       "BY TAXI: £15-20\n\n" +
                       "Call ahead: 0800-123-456",
                "buttons": [
                    {"title": "Open in maps", "payload": "/open_maps"},
                    {"title": "Call taxi", "payload": "/call_taxi"},
                    {"title": "Back", "payload": "/go_to_ae"}
                ]
            })

            return responses
        # Urgent care
        if "/urgent_care" in message:
            responses.append({
                "recipient_id": sender_id,
                "text": "🏥 URGENT CARE OPTIONS\n\n" +
                       "1. Walk-in Centre (8am-8pm)\n" +
                       "2. Minor Injuries Unit\n" +
                       "3. GP Out-of-hours\n" +
                       "4. NHS 111 Service\n\n" +
                       "No appointment needed",
                "buttons": [
                    {"title": "Find nearest", "payload": "/find_urgent_care"},
                    {"title": "Call 111", "payload": "/call_111"},
                    {"title": "Go to A&E", "payload": "/go_to_ae"}
                ]
            })

        # Greeting - ONLY if no other response was added
        if not responses:
            responses.append({
                "recipient_id": sender_id,
                "text": "HEALTHCARE TRIAGE SYSTEM\n\n" +
                       "I can help you with:\n\n" +
                       "• Symptom assessment & triage\n" +
                       "• Appointment scheduling\n" +
                       "• Emergency assistance\n" +
                       "• Medical guidance\n\n" +
                       "How can I assist you today?",
                "buttons": [
                    {"title": "I have symptoms", "payload": "/describe_symptoms"},
                    {"title": "Schedule appointment", "payload": "/schedule_appointment"},
                    {"title": "Emergency help", "payload": "/emergency_help"},
                    {"title": "Speak to nurse", "payload": "/nurse"}
                ]
            })

        return responses

bot = HealthcareBot()

@app.route('/webhooks/rest/webhook', methods=['POST'])
def webhook():
    """Main webhook endpoint compatible with Rasa REST channel"""
    data = request.json
    sender_id = data.get('sender', 'default')
    message = data.get('message', '')

    print(f"\n[WEBHOOK] Received message: '{message}' from sender: {sender_id}")

    # Process message and get responses
    responses = bot.process_message(message, sender_id)

    print(f"[WEBHOOK] Returning {len(responses)} responses")

    return jsonify(responses)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})

@app.route('/', methods=['GET'])
def index():
    """Root endpoint"""
    return jsonify({
        "name": "Healthcare Triage Chatbot",
        "version": "1.0.0",
        "rasa_compatible": "3.6.0",
        "endpoints": [
            "/webhooks/rest/webhook",
            "/health"
        ]
    })

if __name__ == '__main__':
    print("Healthcare Triage Chatbot Server")
    print("================================")
    print("Starting Rasa-compatible server on http://localhost:5005")
    print("REST endpoint: http://localhost:5005/webhooks/rest/webhook")
    print("\nTest scenarios ready:")
    print("- 'I can't breathe' -> Emergency protocol")
    print("- 'I need an ambulance' -> Ambulance dispatch")
    print("- 'I have a fever' -> Fever assessment")
    print("- 'headache' -> Headache triage")
    print("- 'cough' -> Cough evaluation")
    print("- 'stomach pain' -> Abdominal assessment")
    print("- 'schedule appointment' -> Booking system")
    print("- 'cancel appointment' -> Cancellation")
    print("\nPress Ctrl+C to stop")

    import os
    port = int(os.environ.get("PORT", 5005))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
