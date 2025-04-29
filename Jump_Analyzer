import cv2
import mediapipe as mp
import numpy as np

class JumpAnalyzer:
    def __init__(self, person_height_meters):
        self.person_height_meters = person_height_meters
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose()

    def estimate_center_of_mass(self, landmarks, image_height):
        keypoints = [self.mp_pose.PoseLandmark.LEFT_HIP,
                     self.mp_pose.PoseLandmark.RIGHT_HIP,
                     self.mp_pose.PoseLandmark.LEFT_KNEE,
                     self.mp_pose.PoseLandmark.RIGHT_KNEE,
                     self.mp_pose.PoseLandmark.LEFT_ANKLE,
                     self.mp_pose.PoseLandmark.RIGHT_ANKLE]
        y_positions = [landmarks[pt].y * image_height for pt in keypoints if landmarks[pt].visibility > 0.5]
        if not y_positions:
            return None
        return np.mean(y_positions)

    def estimate_pixel_to_meter_ratio(self, landmarks, image_height):
        head_y = landmarks[self.mp_pose.PoseLandmark.NOSE].y * image_height
        ankle_left_y = landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE].y * image_height
        ankle_right_y = landmarks[self.mp_pose.PoseLandmark.RIGHT_ANKLE].y * image_height
        ankle_y = max(ankle_left_y, ankle_right_y)
        pixel_height = abs(ankle_y - head_y)
        return self.person_height_meters / pixel_height

    def analyze_jump(self, video_path):
        cap = cv2.VideoCapture(video_path)

        com_positions = []
        pixel_to_meter_ratio = None

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            image_height, image_width, _ = frame.shape
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(frame_rgb)

            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                
                com_y = self.estimate_center_of_mass(landmarks, image_height)
                if com_y is not None:
                    com_positions.append(com_y)
                
                if pixel_to_meter_ratio is None:
                    pixel_to_meter_ratio = self.estimate_pixel_to_meter_ratio(landmarks, image_height)

        cap.release()

        if com_positions and pixel_to_meter_ratio:
            lowest_com = max(com_positions)
            highest_com = min(com_positions)
            jump_height_pixels = lowest_com - highest_com
            jump_height_meters = jump_height_pixels * pixel_to_meter_ratio

            return jump_height_meters, com_positions
        else:
            return None, None