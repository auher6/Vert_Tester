import cv2
import mediapipe as mp
import numpy as np
from scipy.signal import find_peaks

class JumpAnalyzer:
    def __init__(self, person_height_meters):
        self.person_height_meters = person_height_meters
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        self.gravity = 9.81  # m/s²

    def estimate_center_of_mass(self, landmarks, image_height):
        """More robust COM estimation using major body joints"""
        keypoints = [
            self.mp_pose.PoseLandmark.LEFT_HIP,
            self.mp_pose.PoseLandmark.RIGHT_HIP,
            self.mp_pose.PoseLandmark.LEFT_SHOULDER,
            self.mp_pose.PoseLandmark.RIGHT_SHOULDER,
            self.mp_pose.PoseLandmark.LEFT_KNEE,
            self.mp_pose.PoseLandmark.RIGHT_KNEE
        ]
        
        visible_points = [
            landmarks[pt].y * image_height 
            for pt in keypoints 
            if landmarks[pt].visibility > 0.7  # Higher confidence threshold
        ]
        
        if len(visible_points) < 4:  # Need at least 4 keypoints
            return None
            
        return np.median(visible_points)  # More robust than mean

    def calculate_flight_time(self, com_positions, fps):
        """More reliable flight time calculation"""
        if len(com_positions) < 15 or fps <= 5:
            return 0.0
        
        # Smooth more aggressively
        smoothed_com = np.convolve(com_positions, np.ones(7)/7, mode='valid')
        
        # Find the lowest point (max y value) before ascent
        lowest_frame = np.argmax(smoothed_com[:len(smoothed_com)//2])
        lowest_com = smoothed_com[lowest_frame]
        
        # Find takeoff (when COM rises above threshold)
        threshold = lowest_com * 0.95  # 5% above lowest
        takeoff_frame = next(
            (i for i in range(lowest_frame, len(smoothed_com)) 
            if smoothed_com[i] < threshold),
            None
        )
        
        if takeoff_frame is None:
            return 0.0
        
        # Find landing (when COM returns to takeoff level)
        landing_frame = next(
            (i for i in range(takeoff_frame + 5, len(smoothed_com))
            if smoothed_com[i] >= threshold),
            None
        )
        
        if landing_frame is None:
            return 0.0
        
        flight_time = (landing_frame - takeoff_frame) / fps
        return (self.gravity * flight_time**2) / 8  # h = gt²/8

    def analyze_jump(self, video_path):
        """Analyze jump using physics-based method"""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None, None

        fps = cap.get(cv2.CAP_PROP_FPS)
        com_positions = []

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            results = self.pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            
            if results.pose_landmarks:
                com_y = self.estimate_center_of_mass(
                    results.pose_landmarks.landmark,
                    frame.shape[0]
                )
                if com_y is not None:
                    com_positions.append(com_y)

        cap.release()

        if len(com_positions) < 10:
            return None, None

        # Calculate jump height using physics
        jump_height = self.calculate_flight_time(com_positions, fps)
        
        return jump_height, com_positions