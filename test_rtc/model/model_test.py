import numpy as np
import math
import time
import cv2
import tensorflow as tf
from HandTrackingModule import HandDetector

cap = cv2.VideoCapture(0)
detector = HandDetector(maxHands=1)

offset = 20
img_size = 300

folder = "data"
counter = 0

width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
target_ratio = 16 / 9
current_ratio = width / height

def add_black_bars_16_9(frame):
    
    if current_ratio > target_ratio:
        # Frame is too wide - add black bars on top/bottom (letterbox)
        target_height = int(width / target_ratio)
        padding = (target_height - height) // 2
        
        # Create black bars
        top_bar = np.zeros((padding, width, 3), dtype=np.uint8)
        bottom_bar = np.zeros((target_height - height - padding, width, 3), dtype=np.uint8)
        
        # Combine
        padded_frame = np.vstack([top_bar, frame, bottom_bar])
        
    elif current_ratio < target_ratio:
        # Frame is too tall - add black bars on left/right (pillarbox)
        target_width = int(height * target_ratio)
        padding = (target_width - width) // 2
        
        # Create black bars
        left_bar = np.zeros((height, padding, 3), dtype=np.uint8)
        right_bar = np.zeros((height, target_width - width - padding, 3), dtype=np.uint8)
        
        # Combine
        padded_frame = np.hstack([left_bar, frame, right_bar])
        
    else:
        # Already 16:9 ratio
        padded_frame = frame
    
    return padded_frame

class GestureDataCollector:
    def __init__(self):
        self.angles_data = []
        
    def exctract_finger_angles(self, landmarks):
        angles = []
        
        # Define connections for each finger (indices of connected landmarks)
        fingers = [
            [0, 1, 2, 3, 4],      # Thumb
            [0, 5, 6, 7, 8],      # Index
            [0, 9, 10, 11, 12],   # Middle
            [0, 13, 14, 15, 16],  # Ring
            [0, 17, 18, 19, 20]   # Pinky
        ]
        
        for finger in fingers:
            # Calculate angles at each joint in the finger
            for i in range(1, len(finger)-1):
                angle = self.compute_angles(landmarks[finger[i-1]],
                                    landmarks[finger[i]],
                                    landmarks[finger[i+1]])
                
                angles.append(angle)
            
        for i in range(1, 4):
            angle = self.compute_angles(landmarks[fingers[i-1][4]],
                                        landmarks[fingers[i][4]],
                                        landmarks[fingers[i+1][4]])
            
            angles.append(angle)
        
        return np.array(angles)
    
    def compute_angles(self, p1, p2, p3):
        p1 = np.array(p1)
        p2 = np.array(p2)
        p3 = np.array(p3)
        
        # Vectors between points
        v1 = p1 - p2
        v2 = p3 - p2
        
        # Calculate angle using dot product
        cosine_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        angle = np.clip(cosine_angle, -1.0, 1.0)
        return angle
    
    def get_count(self):
        return len(self.angles_data)

np.set_printoptions(suppress=True)
collector = GestureDataCollector()
loop = True
landmarks = []

### PATH

model = tf.keras.models.load_model('test_rtc/model/gesture_quiz6.h5')
mean_values = np.load('test_rtc/model/normalization_mean6.npy')
std_values = np.load('test_rtc/model/normalization_std6.npy')

### LOOP

while loop:
    ret, frame = cap.read()
    frame = cv2.flip(frame, 1)
    frame = add_black_bars_16_9(frame)
    hands, img, handLms = detector.findHands(frame, getLms=True)
    if handLms:
        landmarks.clear()
        for id, lm in enumerate(handLms.landmark):
            landmarks.append([lm.x, lm.y, lm.z])
        angles = collector.exctract_finger_angles(landmarks)
        angles = np.array(angles).reshape(1, 18)
        angles_normalized = (angles - mean_values) / std_values
        
        prediction = model.predict(angles_normalized, verbose=0)
        predicted_class_idx = np.argmax(prediction)
        confidence = np.max(prediction)
        
        print(predicted_class_idx)
        print(f"CONFIDENCE: {confidence}")
            
    cv2.imshow("frames", img)
    
    key = cv2.waitKey(1)
    if key == ord("q"):
        loop = False