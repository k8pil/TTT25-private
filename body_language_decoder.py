import mediapipe as mp
import cv2
import numpy as np
import pandas as pd
import pickle
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
import os
import base64


class BodyLanguageDecoder:
    def __init__(self, model_path='Body_language.pkl'):
        """Initialize the decoder with model path"""
        self.mp_drawing, self.mp_holistic = self.setup_mediapipe()
        self.model = self.load_model(model_path)
        self.feature_names = None
        
        # Get feature names if available
        if self.model is not None and hasattr(self.model, 'named_steps') and hasattr(self.model.named_steps.get('standardscaler', None), 'feature_names_in_'):
            self.feature_names = self.model.named_steps['standardscaler'].feature_names_in_

    def setup_mediapipe(self):
        """Set up MediaPipe components"""
        mp_drawing = mp.solutions.drawing_utils  # Drawing helpers
        mp_holistic = mp.solutions.holistic  # Mediapipe Solutions
        return mp_drawing, mp_holistic

    def load_model(self, model_path='Body_language.pkl'):
        """Load the trained model"""
        try:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            return model
        except FileNotFoundError:
            print(f"Model file not found at {model_path}")
            return None
        except Exception as e:
            print(f"Error loading model: {e}")
            return None

    def extract_landmarks(self, results):
        """Extract pose and face landmarks from MediaPipe results"""
        try:
            # Check if pose landmarks exist
            if results.pose_landmarks is None:
                return None
                
            # Check if face landmarks exist  
            if results.face_landmarks is None:
                return None
                
            # Extract Pose landmarks
            pose = results.pose_landmarks.landmark
            pose_row = list(np.array([[landmark.x, landmark.y, landmark.z, landmark.visibility] 
                                    for landmark in pose]).flatten())
            
            # Extract Face landmarks
            face = results.face_landmarks.landmark
            face_row = list(np.array([[landmark.x, landmark.y, landmark.z, landmark.visibility] 
                                    for landmark in face]).flatten())
            
            # Concatenate
            row = pose_row + face_row
            return row
        except Exception as e:
            print(f"Error extracting landmarks: {e}")
            return None

    def process_image(self, image):
        """Process a single image and return the results"""
        with self.mp_holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5) as holistic:
            # Convert to RGB
            if image.shape[2] == 3:
                if cv2.cvtColor(image[:,:,0:3], cv2.COLOR_BGR2RGB).shape == image.shape:
                    rgb_image = cv2.cvtColor(image[:,:,0:3], cv2.COLOR_BGR2RGB)
                else:
                    rgb_image = image
            else:
                rgb_image = image
                
            rgb_image.flags.writeable = False
            
            # Make detections
            results = holistic.process(rgb_image)
            
            # Process landmarks for prediction
            landmarks = self.extract_landmarks(results)
            prediction = None
            probability = None
            
            if landmarks is not None and self.model is not None:
                # Make prediction
                if self.feature_names is not None and len(landmarks) == len(self.feature_names):
                    X = pd.DataFrame([landmarks], columns=self.feature_names)
                else:
                    X = pd.DataFrame([landmarks])
                
                prediction = self.model.predict(X)[0]
                probabilities = self.model.predict_proba(X)[0]
                probability = probabilities[np.argmax(probabilities)]
            
            return {
                'results': results,
                'landmarks': landmarks,
                'prediction': prediction,
                'probability': probability
            }

    def visualize_landmarks(self, image, results):
        """Draw landmarks on the image"""
        # Clone the image to avoid modifying the original
        annotated_image = image.copy()
        
        # Draw face landmarks
        self.mp_drawing.draw_landmarks(
            annotated_image, results.face_landmarks, self.mp_holistic.FACEMESH_TESSELATION,
            self.mp_drawing.DrawingSpec(color=(80,110,10), thickness=1, circle_radius=1),
            self.mp_drawing.DrawingSpec(color=(80,256,121), thickness=1, circle_radius=1)
        )
        
        # Draw right hand landmarks
        self.mp_drawing.draw_landmarks(
            annotated_image, results.right_hand_landmarks, self.mp_holistic.HAND_CONNECTIONS,
            self.mp_drawing.DrawingSpec(color=(80,22,10), thickness=2, circle_radius=4),
            self.mp_drawing.DrawingSpec(color=(80,44,121), thickness=2, circle_radius=2)
        )
        
        # Draw left hand landmarks
        self.mp_drawing.draw_landmarks(
            annotated_image, results.left_hand_landmarks, self.mp_holistic.HAND_CONNECTIONS,
            self.mp_drawing.DrawingSpec(color=(121,22,76), thickness=2, circle_radius=4),
            self.mp_drawing.DrawingSpec(color=(121,44,250), thickness=2, circle_radius=2)
        )
        
        # Draw pose landmarks
        self.mp_drawing.draw_landmarks(
            annotated_image, results.pose_landmarks, self.mp_holistic.POSE_CONNECTIONS,
            self.mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=4),
            self.mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2)
        )
        
        return annotated_image

    def draw_prediction_info(self, image, prediction, probability, results):
        """Draw prediction information on the image"""
        # Clone the image to avoid modifying the original
        annotated_image = image.copy()
        
        if prediction is not None and results.pose_landmarks and results.pose_landmarks.landmark:
            # Grab ear coordinates for text placement
            h, w, _ = annotated_image.shape
            coordinates = tuple(np.multiply(
                np.array(
                    (results.pose_landmarks.landmark[self.mp_holistic.PoseLandmark.LEFT_EAR].x,
                     results.pose_landmarks.landmark[self.mp_holistic.PoseLandmark.LEFT_EAR].y)
                ), [w, h]).astype(int))
            
            # Draw rectangle and text at ear position
            cv2.rectangle(
                annotated_image,
                (coordinates[0], coordinates[1]+5),
                (coordinates[0]+len(prediction)*20, coordinates[1]-30),
                (245, 117, 16), -1
            )
            cv2.putText(
                annotated_image, prediction, coordinates,
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA
            )
        
        # Create status box
        cv2.rectangle(annotated_image, (0,0), (250,60), (245, 117, 16), -1)
        
        # Display class
        cv2.putText(
            annotated_image, 'CLASS', (95,12), 
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA
        )
        if prediction:
            cv2.putText(
                annotated_image, prediction.split(' ')[0], (90,40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA
            )
        
        # Display probability
        cv2.putText(
            annotated_image, 'PROB', (15,12),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA
        )
        if probability:
            cv2.putText(
                annotated_image, str(round(probability, 2)), (10,40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA
            )
        
        return annotated_image

    def process_single_frame(self, frame):
        """Process a single frame and return the annotated image and prediction"""
        try:
            # Process the image
            processed = self.process_image(frame)
            
            if processed['results'] is None:
                return {
                    'success': False,
                    'error': 'No body detected in the image'
                }
            
            # Visualize landmarks
            annotated_image = self.visualize_landmarks(frame, processed['results'])
            
            # Draw prediction info
            if processed['prediction'] is not None:
                annotated_image = self.draw_prediction_info(
                    annotated_image, 
                    processed['prediction'], 
                    processed['probability'], 
                    processed['results']
                )
            
            # Return the results
            return {
                'success': True,
                'prediction': processed['prediction'],
                'probability': processed['probability'],
                'annotated_image': annotated_image
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def process_base64_image(self, base64_image):
        """Process an image received as base64 string"""
        try:
            # Decode base64 image
            image_data = base64.b64decode(base64_image)
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Process the image
            result = self.process_single_frame(img)
            
            # If successful, convert the annotated image back to base64
            if result['success'] and 'annotated_image' in result:
                _, buffer = cv2.imencode('.jpg', result['annotated_image'])
                result['annotated_image_base64'] = base64.b64encode(buffer).decode('utf-8')
                del result['annotated_image']  # Remove the numpy array to avoid serialization issues
            
            return result
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_webcam_feed(self):
        """Get webcam feed for testing (non-Flask usage)"""
        # Initialize webcam
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Cannot open webcam. Exiting.")
            return
        
        print("Starting emotion detection. Press 'q' to quit.")
        
        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    print("Failed to capture frame from webcam. Exiting.")
                    break
                
                # Process frame
                result = self.process_single_frame(frame)
                
                if result['success']:
                    # Show the image
                    cv2.imshow('Body Language Decoder', result['annotated_image'])
                
                # Break loop on 'q' key press
                if cv2.waitKey(10) & 0xFF == ord('q'):
                    break
        
        except KeyboardInterrupt:
            print("Interrupted by user")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            # Release resources
            cap.release()
            cv2.destroyAllWindows()
            print("Resources released. Exiting.")

def train_model(data_path='coordinates.csv', save_path='Body_language.pkl'):
    """Train and save the emotion detection model"""
    try:
        # Load data
        df = pd.read_csv(data_path)
        
        # Split data into X and y
        X = df.drop('class', axis=1)
        y = df['class']
        
        # Create pipeline with column names
        pipeline = Pipeline([
            ('standardscaler', StandardScaler()),
            ('randomforestclassifier', RandomForestClassifier())
        ])
        
        # Train model
        pipeline.fit(X, y)
        
        # Save model
        with open(save_path, 'wb') as f:
            pickle.dump(pipeline, f)
        
        print(f"Model trained and saved to {save_path}")
        return pipeline
    
    except FileNotFoundError:
        print(f"Data file not found at {data_path}")
        return None
    except Exception as e:
        print(f"Error training model: {e}")
        return None

# Example of how to use in a Flask application
"""
from flask import Flask, request, jsonify, render_template
import cv2
import numpy as np
import base64

app = Flask(__name__)

# Initialize the decoder once when the app starts
decoder = BodyLanguageDecoder(model_path='Body_language.pkl')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_image', methods=['POST'])
def process_image():
    if 'image' not in request.json:
        return jsonify({'success': False, 'error': 'No image provided'})
    
    # Get the base64 image from the request
    base64_image = request.json['image'].split(',')[1] if ',' in request.json['image'] else request.json['image']
    
    # Process the image
    result = decoder.process_base64_image(base64_image)
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
"""

if __name__ == "__main__":
    print("Body Language Decoder")
    print("1: Train model")
    print("2: Start real-time detection (webcam)")
    print("3: Exit")
    
    choice = input("Enter your choice (1-3): ")
    
    if choice == '1':
        data_path = input("Enter data file path (default: coordinates.csv): ") or 'coordinates.csv'
        save_path = input("Enter save file path (default: Body_language.pkl): ") or 'Body_language.pkl'
        train_model(data_path, save_path)
    
    elif choice == '2':
        model_path = input("Enter model file path (default: Body_language.pkl): ") or 'Body_language.pkl'
        decoder = BodyLanguageDecoder(model_path)
        decoder.get_webcam_feed()
    
    elif choice == '3':
        print("Exiting...")
    
    else:
        print("Invalid choice") 