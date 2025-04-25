import cv2
import mediapipe as mp
import time
import json
import os
import sqlite3
from datetime import datetime
import threading


class InterviewMetricsTracker:
    def __init__(self):
        # Initialize MediaPipe solutions
        self.mp_hands = mp.solutions.hands
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils

        # Initialize detectors
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            smooth_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # Metrics counters and durations
        self.metrics = {
            "handDetectionCount": 0,
            "handDetectionDuration": 0,
            "lossEyeContactCount": 0,
            "lookingAwayDuration": 0,
            "badPostureCount": 0,
            "badPostureDuration": 0,
        }

        # Status flags and timers
        self.hand_on_screen = False
        self.hand_detection_start_time = 0

        self.looking_away = False
        self.looking_away_start_time = None

        self.bad_posture = False
        self.bad_posture_start_time = 0

        # Session info
        self.session_id = datetime.now().strftime("%Y%m%d%H%M%S")

        # Initialize SQLite database
        self.init_database()

        # Background thread for simulation when no actual video is used
        self.is_running = False
        self.thread = None

    def init_database(self):
        """Initialize SQLite database for storing metrics"""
        data_dir = "data"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        self.db_path = os.path.join(data_dir, "interview_metrics.sqlite")

        # Create connection
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS interview_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hand_detection_count INTEGER NOT NULL,
            hand_detection_duration REAL NOT NULL,
            loss_eye_contact_count INTEGER NOT NULL,
            looking_away_duration REAL NOT NULL,
            bad_posture_count INTEGER NOT NULL,
            bad_posture_duration REAL NOT NULL,
            session_id TEXT,
            user_id TEXT,
            is_auto_save INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        conn.commit()
        conn.close()

    def is_facing_forward(self, face_landmarks):
        """Check if the person is facing forward based on face landmarks"""
        if not face_landmarks:
            return False

        # Get right eye landmarks
        right_eye_outer = face_landmarks.landmark[33]
        right_eye_inner = face_landmarks.landmark[133]

        # Get iris landmarks (indices 468-472)
        iris_landmarks = face_landmarks.landmark[468:473]

        # Compute iris center
        iris_center_x = sum(lm.x for lm in iris_landmarks) / \
            len(iris_landmarks)
        iris_center_y = sum(lm.y for lm in iris_landmarks) / \
            len(iris_landmarks)

        # Calculate eye line vector
        AB_x = right_eye_inner.x - right_eye_outer.x
        AB_y = right_eye_inner.y - right_eye_outer.y

        # Calculate vector from outer eye to iris
        AI_x = iris_center_x - right_eye_outer.x
        AI_y = iris_center_y - right_eye_outer.y

        # Calculate dot product and squared magnitude
        dot = AI_x * AB_x + AI_y * AB_y
        norm2 = AB_x * AB_x + AB_y * AB_y

        if norm2 == 0:
            return False

        # Normalized position along the eye line
        t = dot / norm2

        # Return True if t is between thresholds
        return 0.4 <= t <= 0.6

    def is_bad_posture(self, pose_landmarks):
        """Check if the person has bad posture based on pose landmarks"""
        if not pose_landmarks:
            return False

        # Get head and shoulder landmarks
        head = pose_landmarks.landmark[0]  # Nose
        left_shoulder = pose_landmarks.landmark[11]
        right_shoulder = pose_landmarks.landmark[12]

        # Calculate midpoint between shoulders
        mid_shoulder_x = (left_shoulder.x + right_shoulder.x) / 2
        mid_shoulder_y = (left_shoulder.y + right_shoulder.y) / 2

        # Calculate distance between head and shoulder midpoint
        dx = head.x - mid_shoulder_x
        dy = head.y - mid_shoulder_y
        distance = (dx * dx + dy * dy) ** 0.5

        # Return True if distance is less than threshold
        return distance < 0.3

    def process_frame(self, frame):
        """Process a single frame and update metrics"""
        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        current_time = time.time()

        # Process with hand detector
        hand_results = self.hands.process(rgb_frame)
        if hand_results.multi_hand_landmarks:
            if not self.hand_on_screen:
                self.metrics["handDetectionCount"] += 1
                self.hand_detection_start_time = current_time
                self.hand_on_screen = True
        else:
            if self.hand_on_screen:
                duration = current_time - self.hand_detection_start_time
                self.metrics["handDetectionDuration"] += duration
                self.hand_on_screen = False

        # Process with face mesh
        face_results = self.face_mesh.process(rgb_frame)
        if face_results.multi_face_landmarks:
            # Check if looking away
            looking_forward = self.is_facing_forward(
                face_results.multi_face_landmarks[0])
            if not looking_forward:  # Looking away
                if not self.looking_away:
                    self.metrics["lossEyeContactCount"] += 1
                    self.looking_away_start_time = current_time
                    self.looking_away = True
            else:  # Looking forward
                if self.looking_away and self.looking_away_start_time:
                    duration = current_time - self.looking_away_start_time
                    self.metrics["lookingAwayDuration"] += duration
                    self.looking_away = False

        # Process with pose detector
        pose_results = self.pose.process(rgb_frame)
        if pose_results.pose_landmarks:
            bad_posture = self.is_bad_posture(pose_results.pose_landmarks)
            if bad_posture:
                if not self.bad_posture:
                    self.metrics["badPostureCount"] += 1
                    self.bad_posture_start_time = current_time
                    self.bad_posture = True
            else:
                if self.bad_posture:
                    duration = current_time - self.bad_posture_start_time
                    self.metrics["badPostureDuration"] += duration
                    self.bad_posture = False

        return frame

    def display_metrics(self, frame):
        """Display metrics on the frame"""
        # Display hand detection metrics
        cv2.putText(frame, f"Hand Detection Count: {self.metrics['handDetectionCount']}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Hand Duration: {self.metrics['handDetectionDuration']:.2f}s",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Display eye contact metrics
        cv2.putText(frame, f"Loss Eye Contact Count: {self.metrics['lossEyeContactCount']}",
                    (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Looking Away: {self.metrics['lookingAwayDuration']:.2f}s",
                    (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Display posture metrics
        cv2.putText(frame, f"Bad Posture Count: {self.metrics['badPostureCount']}",
                    (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Bad Posture Duration: {self.metrics['badPostureDuration']:.2f}s",
                    (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        return frame

    def save_metrics(self):
        """Save metrics to JSON file and SQLite database"""
        # Save to JSON file
        output_dir = "data"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{output_dir}/interview_metrics_{timestamp}.json"

        data = {
            "sessionId": self.session_id,
            "timestamp": timestamp,
            **self.metrics
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)

        print(f"Metrics saved to {filename}")

        # Save to SQLite database
        self.save_to_sqlite()

    def save_to_sqlite(self, is_auto_save=False):
        """Save current metrics to SQLite database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # If this is an auto-save, delete previous auto-saves
            if is_auto_save:
                cursor.execute(
                    "DELETE FROM interview_metrics WHERE is_auto_save = 1")

            # Insert metrics into database
            cursor.execute('''
            INSERT INTO interview_metrics (
                hand_detection_count,
                hand_detection_duration,
                loss_eye_contact_count,
                looking_away_duration,
                bad_posture_count,
                bad_posture_duration,
                session_id,
                is_auto_save
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.metrics["handDetectionCount"],
                self.metrics["handDetectionDuration"],
                self.metrics["lossEyeContactCount"],
                self.metrics["lookingAwayDuration"],
                self.metrics["badPostureCount"],
                self.metrics["badPostureDuration"],
                self.session_id,
                1 if is_auto_save else 0
            ))

            conn.commit()

            # Get the ID of the inserted record
            record_id = cursor.lastrowid
            conn.close()

            print(f"Metrics saved to SQLite database (ID: {record_id})")
            return record_id

        except Exception as e:
            print(f"Error saving to SQLite: {str(e)}")
            return None

    def auto_save_metrics(self):
        """Auto-save current metrics to SQLite with auto_save flag"""
        return self.save_to_sqlite(is_auto_save=True)

    def cleanup(self):
        """Release resources and save final metrics"""
        # Update durations if still tracking at end of session
        current_time = time.time()

        if self.hand_on_screen:
            self.metrics["handDetectionDuration"] += (
                current_time - self.hand_detection_start_time)

        if self.looking_away and self.looking_away_start_time:
            self.metrics["lookingAwayDuration"] += (
                current_time - self.looking_away_start_time)

        if self.bad_posture:
            self.metrics["badPostureDuration"] += (
                current_time - self.bad_posture_start_time)

        # Save metrics
        self.save_metrics()

        # Close MediaPipe resources
        self.hands.close()
        self.face_mesh.close()
        self.pose.close()

    def start3(self):
        """Start video analysis in a background thread with simulation for UI integration"""
        if self.thread is not None and self.is_running:
            return False

        self.is_running = True
        self.thread = threading.Thread(target=self._simulate_metrics_update)
        self.thread.daemon = True
        self.thread.start()
        return True

    def _simulate_metrics_update(self):
        """Simulates metrics updates for UI testing without actual video processing"""
        import random

        last_time = time.time()
        while self.is_running:
            current_time = time.time()
            elapsed = current_time - last_time
            last_time = current_time

            # Random chance of hand detection
            if random.random() < 0.2:  # 20% chance of hand appearing
                if not self.hand_on_screen:
                    self.metrics["handDetectionCount"] += 1
                    self.hand_detection_start_time = current_time
                    self.hand_on_screen = True
            else:
                if self.hand_on_screen:
                    duration = current_time - self.hand_detection_start_time
                    self.metrics["handDetectionDuration"] += duration
                    self.hand_on_screen = False

            # Random chance of looking away
            if random.random() < 0.15:  # 15% chance of looking away
                if not self.looking_away:
                    self.metrics["lossEyeContactCount"] += 1
                    self.looking_away_start_time = current_time
                    self.looking_away = True
            else:
                if self.looking_away and self.looking_away_start_time:
                    duration = current_time - self.looking_away_start_time
                    self.metrics["lookingAwayDuration"] += duration
                    self.looking_away = False

            # Random chance of bad posture
            if random.random() < 0.1:  # 10% chance of bad posture
                if not self.bad_posture:
                    self.metrics["badPostureCount"] += 1
                    self.bad_posture_start_time = current_time
                    self.bad_posture = True
            else:
                if self.bad_posture:
                    duration = current_time - self.bad_posture_start_time
                    self.metrics["badPostureDuration"] += duration
                    self.bad_posture = False

            # Sleep to simulate 0.5 second intervals
            time.sleep(0.5)

    def close(self):
        """Stop the analysis and save final metrics"""
        if self.is_running:
            self.is_running = False
            if self.thread:
                self.thread.join(timeout=1.0)
            self.cleanup()

    def get_current_metrics(self):
        """Get current metrics as a formatted string"""
        return (
            f"Hand Detection - Count: {self.metrics['handDetectionCount']}, Duration: {self.metrics['handDetectionDuration']:.2f}s\n"
            f"Eye Contact - Loss Count: {self.metrics['lossEyeContactCount']}, Looking Away: {self.metrics['lookingAwayDuration']:.2f}s\n"
            f"Posture - Bad Count: {self.metrics['badPostureCount']}, Bad Duration: {self.metrics['badPostureDuration']:.2f}s"
        )

    def get_metrics_dict(self):
        """Get current metrics as a dictionary"""
        return self.metrics.copy()


def main():
    tracker = InterviewMetricsTracker()
    cap = cv2.VideoCapture(0)  # Use default camera

    # Check if camera opened successfully
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    print("Starting interview metrics tracking...")
    print("Running in background mode - no video output")
    print("Press Ctrl+C to stop tracking and save final metrics")

    last_auto_save = time.time()
    auto_save_interval = 30  # Auto-save every 30 seconds

    # Frame processing control
    frame_interval = 1  # Process every 3rd frame
    frame_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to capture frame.")
                break

            # Only process every Nth frame to reduce CPU usage
            frame_count += 1
            if frame_count % frame_interval != 0:
                time.sleep(0.05)  # Short sleep when skipping frames
                continue

            # Process frame and get metrics
            tracker.process_frame(frame)

            # Print metrics to console (less frequently)
            # Update console every ~30 frames
            if frame_count % (frame_interval * 10) == 0:
                print("\033[H\033[J")  # Clear console
                print(
                    f"Hand Detection - Detection Count: {tracker.metrics['handDetectionCount']}, Total Duration: {tracker.metrics['handDetectionDuration']:.2f}s")
                print(
                    f"Eye Contact Detection - Loss Eye Contact Count: {tracker.metrics['lossEyeContactCount']}, Looking Away: {tracker.metrics['lookingAwayDuration']:.2f}s")
                print(
                    f"Bad Posture Monitoring - Bad Posture Count: {tracker.metrics['badPostureCount']}, Bad Posture Duration: {tracker.metrics['badPostureDuration']:.2f}s")
                print(
                    f"\nAuto-saving every {auto_save_interval} seconds. Press Ctrl+C to quit.")

            # Auto-save at regular intervals
            current_time = time.time()
            if current_time - last_auto_save > auto_save_interval:
                tracker.auto_save_metrics()
                last_auto_save = current_time
                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] Auto-saved metrics to database (overwrites previous auto-save)")

            # Add delay to reduce processing frequency
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected. Saving final metrics...")

    finally:
        cap.release()
        if cv2.getWindowProperty('Interview Metrics Tracking', cv2.WND_PROP_VISIBLE) >= 0:
            cv2.destroyAllWindows()
        tracker.cleanup()

        # Print final metrics
        print("\nFinal Metrics:")
        print(
            f"Hand Detection - Detection Count: {tracker.metrics['handDetectionCount']}, Total Duration: {tracker.metrics['handDetectionDuration']:.2f}s")
        print(
            f"Eye Contact Detection - Loss Eye Contact Count: {tracker.metrics['lossEyeContactCount']}, Looking Away: {tracker.metrics['lookingAwayDuration']:.2f}s")
        print(
            f"Bad Posture Monitoring - Bad Posture Count: {tracker.metrics['badPostureCount']}, Bad Posture Duration: {tracker.metrics['badPostureDuration']:.2f}s")


if __name__ == "__main__":
    main()
