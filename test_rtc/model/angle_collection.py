import numpy as np
import math
import time
import cv2
from HandTrackingModule import HandDetector

cap = cv2.VideoCapture(1)
detector = HandDetector(maxHands=1)

offset = 20
img_size = 300

folder = "data"
counter = 0

width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
target_ratio = 16 / 9
current_ratio = width / height

def add_padding(frame):
    # Dimensi terlalu lebar
    if current_ratio > target_ratio:
        target_height = int(width / target_ratio)
        padding = (target_height - height) // 2
        top_bar = np.zeros((padding, width, 3), dtype=np.uint8)
        bottom_bar = np.zeros((target_height - height - padding, width, 3), dtype=np.uint8)
        padded_frame = np.vstack([top_bar, frame, bottom_bar])
        
    # Dimensi terlalu tinggi
    elif current_ratio < target_ratio:
        target_width = int(height * target_ratio)
        padding = (target_width - width) // 2
        left_bar = np.zeros((height, padding, 3), dtype=np.uint8)
        right_bar = np.zeros((height, target_width - width - padding, 3), dtype=np.uint8)
        padded_frame = np.hstack([left_bar, frame, right_bar])
    
    # Dimensi sudah 16:9
    else:
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
        
        # Dua vektor untuk menghitung sudut pada titik p2
        v1 = p1 - p2
        v2 = p3 - p2
        
        # Menghitung cos sudut menggunakan dot product
        cosine_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        angle = np.clip(cosine_angle, -1.0, 1.0)
        return angle
    
    def add_sample(self, angles):
        """Add a single gesture sample"""
        self.angles_data.append(angles)
    
    def save_all(self, filename):
        """Save all collected data"""
        angles_array = np.array(self.angles_data)
        
        np.save(filename, arr=angles_array)
        
        print(f"Saved {len(self.angles_data)} samples to {filename}")
    
    def get_count(self):
        return len(self.angles_data)

collector = GestureDataCollector()
loop = True
landmarks = []

while loop:
    ret, frame = cap.read()
    frame = cv2.flip(frame, 1)
    frame = add_padding(frame)
    hands, img, handLms = detector.findHands(frame, getLms=True)
    if handLms:
        landmarks.clear()
        for id, lm in enumerate(handLms.landmark):
            landmarks.append([lm.x, lm.y, lm.z])
        angles = collector.exctract_finger_angles(landmarks)
            
    
    cv2.imshow("frames", img)
    
    key = cv2.waitKey(1)
    if key == ord("s"):
        collector.add_sample(angles)
        counter += 1
        print(f"{counter}. {angles}")
    elif key == ord("e"):
        collector.save_all('test_rtc/model/data/no')
        loop = False