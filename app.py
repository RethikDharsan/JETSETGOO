from flask import Flask, request, render_template
import requests
import cv2
import pytesseract
from googletrans import Translator
import numpy as np
from datetime import datetime, timedelta

app = Flask(__name__)
translator = Translator()

# Set the path to the Tesseract executable
pytesseract.pytesseract.tesseract_cmd = r'D:\T\tesseract.exe'  # Update this path if needed

# Root route
@app.route('/')
def home():
    return render_template('home.html')  # Render the homepage with two options

# Route for live flight updates
@app.route('/flight', methods=['GET', 'POST'])
def get_flight_info():
    if request.method == 'POST':
        flight_code = request.form.get('flight_code')
        if not flight_code:
            return render_template('flight_result.html', error="Flight code is required")
        
        # API URL for flight data
        api_url = f"http://api.aviationstack.com/v1/flights?access_key=dc515f51f7f96227f7c4e2e9f8fde5c0&flight_iata={flight_code}"
        response = requests.get(api_url)
        
        if response.status_code == 200:
            flight_data = response.json()
            if "data" in flight_data and flight_data["data"]:
                heathrow_flights = [
                    flight for flight in flight_data["data"]
                    if flight.get("departure", {}).get("airport") == "Heathrow" or
                       flight.get("arrival", {}).get("airport") == "Heathrow"
                ]
                if not heathrow_flights:
                    return render_template('flight_result.html', error="No flights found for Heathrow Airport")

                processed_flights = []
                for flight in heathrow_flights:
                    departure = flight.get("departure", {})
                    arrival = flight.get("arrival", {})
                    delays = flight.get("delays", 0)  # Delay in minutes
                    departure_time = convert_to_uk_time(departure.get("scheduled"))
                    arrival_time = convert_to_uk_time(arrival.get("scheduled"))
                    updated_departure_time = calculate_updated_time(departure_time, delays)
                    updated_arrival_time = calculate_updated_time(arrival_time, delays)

                    departure_airport = departure.get("airport", "Unknown")
                    arrival_airport = arrival.get("airport", "Unknown")

                    if departure_airport == "Heathrow":
                        flight_type = "Departure"
                        terminal = departure.get("terminal", "Unknown")
                        other_airport = f"{arrival.get('country', 'Unknown')} - {arrival_airport}"
                        other_time = arrival_time
                        updated_other_time = updated_arrival_time
                    else:
                        flight_type = "Arrival"
                        terminal = arrival.get("terminal", "Unknown")
                        other_airport = f"{departure.get('country', 'Unknown')} - {departure_airport}"
                        other_time = departure_time
                        updated_other_time = updated_departure_time

                    processed_flights.append({
                        "date": departure_time.strftime("%A, %d %B %Y") if departure_time else "Unknown",
                        "flight_code": flight.get("flight", {}).get("iata", "Unknown"),
                        "flight_name": flight.get("airline", {}).get("name", "Unknown"),
                        "flight_type": flight_type,
                        "departure_time": departure_time.strftime("%I:%M %p") if departure_time else "Unknown",
                        "arrival_time": other_time.strftime("%I:%M %p") if other_time else "Unknown",
                        "other_airport": other_airport,
                        "terminal": terminal,
                        "delays": f"{delays} minutes" if delays else "No delays",
                        "updated_time": updated_other_time.strftime("%I:%M %p") if delays else "No updates"
                    })

                return render_template('flight_result.html', flights=processed_flights)
            else:
                return render_template('flight_result.html', error="No flight data found")
        else:
            return render_template('flight_result.html', error="Unable to fetch flight data")
    return render_template('flight.html')  # Render the flight search page

# Route for text translation
@app.route('/translate', methods=['GET', 'POST'])
def translate_text():
    if request.method == 'POST':
        text = request.form.get('text')
        target_language = request.form.get('target_language', 'en')

        if not text:
            return render_template('translate_result.html', error="Text is required")

        translated = translator.translate(text, dest=target_language)
        return render_template('translate_result.html', translated_text=translated.text)
    return render_template('translate.html')  # Render the translation page

# Route for image translation
@app.route('/translate-image', methods=['POST'])
def translate_image():
    try:
        file = request.files.get('image')
        target_language = request.form.get('target_language', 'en')

        if not file or not file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            return render_template('translate_result.html', error="Invalid file type. Please upload an image.")

        # Read image and extract text
        image = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            return render_template('translate_result.html', error="Could not read the image. Please upload a valid image.")

        extracted_text = pytesseract.image_to_string(image)

        # Translate extracted text
        translated = translator.translate(extracted_text, dest=target_language)
        return render_template('translate_result.html', extracted_text=extracted_text, translated_text=translated.text)

    except Exception as e:
        return render_template('translate_result.html', error=f"An error occurred: {str(e)}")

# Helper function to convert time to UK time (UTC+0)
def convert_to_uk_time(time_str):
    if not time_str:
        return None
    return datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S%z").astimezone(tz=None)

# Helper function to calculate updated time with delays
def calculate_updated_time(original_time, delay_minutes):
    if not original_time or not delay_minutes:
        return original_time
    return original_time + timedelta(minutes=delay_minutes)

# Start the application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # Use Flask's built-in server for local development
