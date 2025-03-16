import numpy as np
import cv2
import pickle
import pyttsx3
from datetime import datetime, timedelta
import pytz
import random
import time
import sys
import os
import requests
from threading import Thread, Event
import json

# Constants
frameWidth = 640
frameHeight = 480
brightness = 180
threshold = 0.75
font = cv2.FONT_HERSHEY_SIMPLEX

# System control flags
system_running = True
camera_enabled = True
volume_level = 50
stop_event = Event()

# Driver details
if len(sys.argv) > 1:
    driver_name = sys.argv[1]
else:
    driver_name = "Driver" 

# Assistant details
assistant_name = "Robin"

def initialize_system():
    try:
        # Camera setup
        cap = cv2.VideoCapture(0)
        cap.set(3, frameWidth)
        cap.set(4, frameHeight)
        cap.set(10, brightness)
        
        if not cap.isOpened():
            raise Exception("Failed to initialize camera")

        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(script_dir, 'model_trained.p')

        # Load the model
        with open(model_path, "rb") as pickle_in:
            model = pickle.load(pickle_in)

        # Initialize text-to-speech
        engine = pyttsx3.init()
        engine.setProperty('volume', volume_level / 100.0)

        return cap, model, engine
    except Exception as e:
        send_error(f"System initialization failed: {str(e)}")
        raise

def send_system_status(status):
    try:
        requests.post('http://localhost:5000/system_status', 
                     json={'status': status},
                     headers={'Content-Type': 'application/json'})
    except Exception as e:
        print(f"Error sending system status: {e}")

def send_sign_detection(sign_name):
    try:
        requests.post('http://localhost:5000/sign_detected', 
                     json={'name': sign_name},
                     headers={'Content-Type': 'application/json'})
    except Exception as e:
        print(f"Error sending sign detection: {e}")

def send_error(error_message):
    try:
        requests.post('http://localhost:5000/error',
                     json={'message': error_message},
                     headers={'Content-Type': 'application/json'})
    except Exception as e:
        print(f"Error sending error message: {e}")

def grayscale(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

def equalize(img):
    return cv2.equalizeHist(img)

def preprocessing(img):
    img = grayscale(img)
    img = equalize(img)
    img = img.astype('float32') / 255
    return img

def getClassName(classNo):
    classes = [
        'Speed Limit 20 km/h', 'Speed Limit 30 km/h', 'Speed Limit 50 km/h',
        'Speed Limit 60 km/h', 'Speed Limit 70 km/h', 'Speed Limit 80 km/h',
        'End of Speed Limit 80 km/h', 'Speed Limit 100 km/h', 'Speed Limit 120 km/h',
        'No passing', 'No passing for vehicles over 3.5 metric tons', 
        'Right-of-way at the next intersection', 'Priority road', 'Yield', 'Stop', 
        'No vehicles', 'Vehicles over 3.5 metric tons prohibited', 'No entry', 
        'General caution', 'Dangerous curve to the left', 'Dangerous curve to the right', 
        'Double curve', 'Bumpy road', 'Slippery road', 'Road narrows on the right', 
        'Road work', 'Traffic signals', 'Pedestrians', 'Children crossing', 
        'Bicycles crossing', 'Beware of ice/snow', 'Wild animals crossing', 
        'End of all speed and passing limits', 'Turn right ahead', 'Turn left ahead', 
        'Ahead only', 'Go straight or right', 'Go straight or left', 'Keep right', 
        'Keep left', 'Roundabout mandatory', 'End of no passing', 
        'End of no passing by vehicles over 3.5 metric tons'
    ]
    return classes[classNo] if classNo < len(classes) else "Unknown"

def get_greeting():
    tz = pytz.timezone('Africa/Nairobi')
    now = datetime.now(tz)
    hour = now.hour

    if 5 <= hour < 12:
        return "Good Morning"
    elif 12 <= hour < 18:
        return "Good Afternoon"
    else:
        return "Good Evening"

def main():
    try:
        cap, model, engine = initialize_system()
        
        # Send initial system status
        send_system_status('starting')

        # Play greeting immediately
        greeting = get_greeting()
        engine.say(f"{greeting}, {driver_name}. I'm {assistant_name}, your driving aid today. All systems are now up and running. Lets move.")
        engine.runAndWait()

        # Send system status to indicate the system is running
        send_system_status('running')

        last_spoken_class = None
        detection_count = 0
        last_detection_time = datetime.now()

        while not stop_event.is_set():
            if not system_running:
                time.sleep(0.1)
                continue

            if not camera_enabled:
                time.sleep(0.1)
                continue

            success, imgOriginal = cap.read()
            if not success:
                send_error("Failed to capture frame")
                continue

            try:
                img = cv2.resize(imgOriginal, (32, 32))
                img = preprocessing(img)
                img = img.reshape(1, 32, 32, 1)

                predictions = model.predict(img)
                classIndex = np.argmax(predictions, axis=1)[0]
                probabilityValue = np.max(predictions)

                if probabilityValue > threshold:
                    class_name = getClassName(classIndex)
                    Thread(target=send_sign_detection, args=(class_name,)).start()

                    cv2.putText(imgOriginal, f"CLASS: {classIndex} {class_name}",
                              (20, 35), font, 0.75, (0, 0, 255), 2, cv2.LINE_AA)
                    cv2.putText(imgOriginal, f"PROBABILITY: {round(probabilityValue * 100, 2)}%",
                              (20, 75), font, 0.75, (0, 0, 255), 2, cv2.LINE_AA)

                    if class_name != last_spoken_class and not engine._inLoop:
                        response = random.choice([
                            f"Hello again, {driver_name}. Please be on the lookout for {class_name}.",
                            f"Hey {driver_name}, heads up! There's a {class_name}.",
                            f"Just a heads-up, {driver_name}. There's a {class_name}.",
                            f"Stay alert, {driver_name}! A {class_name} is ahead.",
                            f"{driver_name}, watch out for the {class_name}."
                        ])
                        engine.say(response)
                        Thread(target=engine.runAndWait).start()
                        last_spoken_class = class_name
                        detection_count += 1
                        last_detection_time = datetime.now()

                if cv2.getWindowProperty('Result', cv2.WND_PROP_VISIBLE) >= 0:
                    cv2.imshow("Processed Image", cv2.cvtColor(img, cv2.COLOR_GRAY2BGR))
                    cv2.imshow("Result", imgOriginal)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            except Exception as e:
                send_error(f"Error processing frame: {str(e)}")
                continue

    except Exception as e:
        send_error(f"System error: {str(e)}")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        send_system_status('stopped')

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        stop_event.set()
        print("\nGracefully shutting down...")
    except Exception as e:
        send_error(f"Fatal error: {str(e)}")