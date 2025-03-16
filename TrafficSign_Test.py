import numpy as np
import cv2
import pickle
import pyttsx3
from datetime import datetime, timedelta
import pytz
import random
import time

# Constants
frameWidth = 640
frameHeight = 480
brightness = 180
threshold = 0.75
font = cv2.FONT_HERSHEY_SIMPLEX

# Driver details
driver_name = "Ken"  # Pass the driver's name here
assistant_name = "Robin"  # Name of the driving aid

# Camera setup
cap = cv2.VideoCapture(0)
cap.set(3, frameWidth)
cap.set(4, frameHeight)
cap.set(10, brightness)

# Load the trained model
pickle_in = open("model_trained.p", "rb")
model = pickle.load(pickle_in)

# Initialize the text-to-speech engine
engine = pyttsx3.init()

# Variables to store the last spoken class and detection count
last_spoken_class = None
detection_count = 0  # Counter to track the number of detections
last_detection_time = datetime.now()  # Track the time of the last detection

# Pool of responses for subsequent detections
subsequent_responses = [
    f"Hello again, {driver_name}. Please be on the lookout for {{sign}}, {{distance}} ahead.",
    f"Hey {driver_name}, heads up! There's a {{sign}} {{distance}} ahead.",
    f"Just a heads-up, {driver_name}. There's a {{sign}} {{distance}} ahead.",
    f"Stay alert, {driver_name}! A {{sign}} is {{distance}} ahead.",
    f"{driver_name}, watch out for the {{sign}} {{distance}} ahead."
]

# Pool of driving jokes and quotes
driving_jokes = [
    "Why did the traffic light turn red? You would too if you had to change in the middle of the street!",
    "What do you call a line of cars singing Christmas songs? A traffic jam!",
    "Why don’t cars ever get lost? Because they always follow the road-map!",
    "Remember, driving is not a race. It’s a journey. Enjoy the ride!",
    "Stay alert! The road is full of surprises, just like a box of chocolates."
]

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
    # Get current time in East Africa Time (EAT)
    tz = pytz.timezone('Africa/Nairobi')
    now = datetime.now(tz)
    hour = now.hour

    if 5 <= hour < 12:
        return "Good Morning"
    elif 12 <= hour < 18:
        return "Good Afternoon"
    else:
        return "Good Evening"

def estimate_distance(object_width_pixels, focal_length=500, known_width=0.5):
    """
    Estimate distance to the object using simple pinhole camera model.
    object_width_pixels: Width of the object in pixels.
    focal_length: Focal length of the camera (pre-calibrated).
    known_width: Known width of the object in meters (e.g., average traffic sign width).
    """
    if object_width_pixels == 0:
        return 0
    return (known_width * focal_length) / object_width_pixels

def tell_joke_or_quote():
    joke_or_quote = random.choice(driving_jokes)
    engine.say(joke_or_quote)
    engine.runAndWait()

while True:
    # Read image
    success, imgOriginal = cap.read()
    if not success:
        print("Failed to capture frame.")
        break

    # Process image
    img = cv2.resize(imgOriginal, (32, 32))
    img = preprocessing(img)
    img = img.reshape(1, 32, 32, 1)

    # Predict
    predictions = model.predict(img)
    classIndex = np.argmax(predictions, axis=1)[0]
    probabilityValue = np.max(predictions)

    # Display results
    if probabilityValue > threshold:
        class_name = getClassName(classIndex)
        cv2.putText(imgOriginal, f"CLASS: {classIndex} {class_name}",
                    (20, 35), font, 0.75, (0, 0, 255), 2, cv2.LINE_AA)
        cv2.putText(imgOriginal, f"PROBABILITY: {round(probabilityValue * 100, 2)}%", 
                    (20, 75), font, 0.75, (0, 0, 255), 2, cv2.LINE_AA)

        # Estimate distance to the sign (simplified)
        object_width_pixels = 100  # Placeholder: Replace with actual object width in pixels
        distance = estimate_distance(object_width_pixels)
        distance_text = f"{int(distance)} meters ahead" if distance > 0 else "ahead"

        # Speak the class name if it's different from the last spoken class
        if class_name != last_spoken_class:
            if detection_count == 0:
                # First detection: Greet the driver and introduce the system
                greeting = get_greeting()
                engine.say(f"{greeting}, {driver_name}. My name is {assistant_name}, and I will be your driving aid today.")
                engine.say(f"Please be on the lookout for {class_name}, {distance_text}.")
            else:
                # Subsequent detections: Use randomized responses
                response = random.choice(subsequent_responses)
                response = response.format(sign=class_name, distance=distance_text)
                engine.say(response)
            engine.runAndWait()
            last_spoken_class = class_name
            detection_count += 1
            last_detection_time = datetime.now()  # Update last detection time

    # Check if no sign has been detected for 5 minutes
    if (datetime.now() - last_detection_time).total_seconds() > 300:  # 300 seconds = 5 minutes
        tell_joke_or_quote()
        last_detection_time = datetime.now()  # Reset the timer

    cv2.imshow("Processed Image", cv2.cvtColor(img, cv2.COLOR_GRAY2BGR))
    cv2.imshow("Result", imgOriginal)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()