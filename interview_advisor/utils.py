import os
from dotenv import load_dotenv
import json
import tempfile
import time
from typing import Dict, List, Any, Optional
import sqlite3

# Load environment variables
load_dotenv()


def load_json_file(file_path: str) -> Dict:
    """Load data from a JSON file."""
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading JSON file: {e}")
        return {}


def save_json_file(data: Dict, file_path: str) -> bool:
    """Save data to a JSON file."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2)
        return True
    except Exception as e:
        print(f"Error saving file {file_path}: {e}")
        return False


def create_temp_file(content: str, suffix: str = '.txt') -> str:
    """Create a temporary file with the given content."""
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp.write(content.encode('utf-8'))
    temp.close()
    return temp.name


def read_text_file(file_path: str) -> str:
    """Read text from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return ""


def ensure_directory(path: str) -> None:
    """Ensure a directory exists, creating it if necessary."""
    os.makedirs(path, exist_ok=True)


def validate_api_keys() -> bool:
    """Validate required API keys are present in environment."""
    required_keys = ["GOOGLE_API_KEY"]
    optional_keys = ["ELEVENLABS_API_KEY"]

    missing_keys = [key for key in required_keys if not os.getenv(key)]

    if missing_keys:
        print(f"Missing required API keys: {', '.join(missing_keys)}")
        return False

    missing_optional = [key for key in optional_keys if not os.getenv(key)]
    if missing_optional:
        print(f"Missing optional API keys: {', '.join(missing_optional)}")

    return True


class DatabaseManager:
    """Manages database connections and operations for tracking metrics."""

    def __init__(self, db_path: str = "interview_metrics.db"):
        """Initialize the database manager."""
        self.db_path = db_path
        self.conn = None
        try:
            self.initialize_database()
        except Exception as e:
            print(f"Failed to initialize database: {e}")
            import traceback
            traceback.print_exc()
            self.conn = None

    def initialize_database(self) -> None:
        """Create tables if they don't exist."""
        try:
            print(f"Connecting to database at {self.db_path}")
            self.conn = sqlite3.connect(self.db_path)
            cursor = self.conn.cursor()

            # Create session table
            print("Creating tables if they don't exist...")
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                resume_id TEXT,
                questions_count INTEGER DEFAULT 0
            )
            ''')

            # Create table for audio metrics
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS audio_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TIMESTAMP,
                fluency_score REAL,
                is_stuttering INTEGER,
                word_count INTEGER,
                filler_word_count INTEGER,
                speech_rate REAL,
                transcript TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
            ''')

            # Create table for posture/eye/hand metrics
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS posture_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TIMESTAMP,
                hand_detected INTEGER,
                hand_detection_duration REAL,
                not_facing_camera INTEGER,
                not_facing_duration REAL,
                bad_posture_detected INTEGER,
                bad_posture_duration REAL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
            ''')

            # Create table for interview analysis results
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS interview_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                strengths TEXT,
                areas_for_improvement TEXT,
                communication_rating TEXT,
                technical_rating TEXT,
                recommendations TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
            ''')

            self.conn.commit()
            print(f"Database initialized at {self.db_path}")
        except sqlite3.Error as e:
            print(f"SQLite error initializing database: {e}")
            if self.conn:
                self.conn = None
            raise
        except Exception as e:
            print(f"Error initializing database: {e}")
            import traceback
            traceback.print_exc()
            if self.conn:
                self.conn = None
            raise

    def create_session(self, session_id: str, resume_id: Optional[str] = None) -> bool:
        """Create a new session record."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO sessions (session_id, start_time, resume_id) VALUES (?, ?, ?)",
                (session_id, time.time(), resume_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error creating session: {e}")
            return False

    def end_session(self, session_id: str, questions_count: int) -> bool:
        """Update session with end time and questions count."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE sessions SET end_time = ?, questions_count = ? WHERE session_id = ?",
                (time.time(), questions_count, session_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error ending session: {e}")
            return False

    def save_audio_metrics(self, session_id: str, metrics: Dict[str, Any]) -> bool:
        """Save audio analysis metrics."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT INTO audio_metrics 
                   (session_id, timestamp, fluency_score, is_stuttering, 
                    word_count, filler_word_count, speech_rate, transcript)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    time.time(),
                    metrics.get("fluency_score", 0),
                    1 if metrics.get("is_stuttering", False) else 0,
                    metrics.get("word_count", 0),
                    metrics.get("filler_word_count", 0),
                    metrics.get("speech_rate", 0),
                    metrics.get("transcription", "")
                )
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saving audio metrics: {e}")
            return False

    def save_posture_metrics(self, session_id: str, metrics: Dict[str, Any]) -> bool:
        """Save posture/eye/hand detection metrics."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT INTO posture_metrics 
                   (session_id, timestamp, hand_detected, hand_detection_duration,
                    not_facing_camera, not_facing_duration, 
                    bad_posture_detected, bad_posture_duration)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    time.time(),
                    1 if metrics.get("hand_detected", False) else 0,
                    metrics.get("hand_detection_duration", 0),
                    1 if metrics.get("not_facing_camera", False) else 0,
                    metrics.get("not_facing_duration", 0),
                    1 if metrics.get("bad_posture_detected", False) else 0,
                    metrics.get("bad_posture_duration", 0)
                )
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saving posture metrics: {e}")
            return False

    def save_analysis_results(self, session_id: str, analysis: Dict[str, Any]) -> bool:
        """Save interview analysis results."""
        try:
            strengths = json.dumps(analysis.get("strengths", []))
            areas = json.dumps(analysis.get("areas_for_improvement", []))
            recommendations = json.dumps(
                analysis.get("skill_recommendations", []))

            comm = analysis.get("communication_skills", {})
            tech = analysis.get("technical_assessment", {})

            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT INTO interview_analysis 
                   (session_id, strengths, areas_for_improvement, 
                    communication_rating, technical_rating, recommendations)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    strengths,
                    areas,
                    comm.get("rating", "N/A"),
                    tech.get("rating", "N/A"),
                    recommendations
                )
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saving analysis results: {e}")
            return False

    def get_session_metrics(self, session_id: str) -> Dict[str, Any]:
        """Get all metrics for a specific session."""
        try:
            cursor = self.conn.cursor()

            # Get session info
            cursor.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,))
            session = cursor.fetchone()

            if not session:
                return {"error": "Session not found"}

            # Get audio metrics
            cursor.execute(
                "SELECT * FROM audio_metrics WHERE session_id = ?", (session_id,))
            audio_metrics = cursor.fetchall()

            # Get posture metrics
            cursor.execute(
                "SELECT * FROM posture_metrics WHERE session_id = ?", (session_id,))
            posture_metrics = cursor.fetchall()

            # Get analysis results
            cursor.execute(
                "SELECT * FROM interview_analysis WHERE session_id = ?", (session_id,))
            analysis = cursor.fetchone()

            return {
                "session": session,
                "audio_metrics": audio_metrics,
                "posture_metrics": posture_metrics,
                "analysis": analysis
            }
        except Exception as e:
            print(f"Error getting session metrics: {e}")
            return {"error": str(e)}

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get a list of all sessions with basic information."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT session_id as id, start_time, end_time, resume_id, questions_count 
                FROM sessions 
                ORDER BY start_time DESC
            """)

            # Convert tuples to dictionaries
            columns = ["id", "start_time", "end_time",
                       "resume_id", "questions_count"]
            sessions = []

            for row in cursor.fetchall():
                session = {}
                for i, column in enumerate(columns):
                    session[column] = row[i]
                sessions.append(session)

            return sessions
        except Exception as e:
            print(f"Error getting all sessions: {e}")
            return []

    def get_session_details(self, session_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific session."""
        try:
            cursor = self.conn.cursor()

            # Get session info
            cursor.execute("""
                SELECT session_id, start_time, end_time, resume_id, questions_count 
                FROM sessions 
                WHERE session_id = ?
            """, (session_id,))

            row = cursor.fetchone()
            if not row:
                return {}

            # Convert to dictionary
            columns = ["session_id", "start_time",
                       "end_time", "resume_id", "questions_count"]
            session = {}
            for i, column in enumerate(columns):
                session[column] = row[i]

            # Get counts of metrics
            cursor.execute(
                "SELECT COUNT(*) FROM audio_metrics WHERE session_id = ?", (session_id,))
            session["audio_metrics_count"] = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM posture_metrics WHERE session_id = ?", (session_id,))
            session["posture_metrics_count"] = cursor.fetchone()[0]

            # Check if analysis exists
            cursor.execute(
                "SELECT COUNT(*) FROM interview_analysis WHERE session_id = ?", (session_id,))
            session["has_analysis"] = cursor.fetchone()[0] > 0

            return session
        except Exception as e:
            print(f"Error getting session details: {e}")
            return {}

    def get_audio_metrics(self, session_id: str) -> List[Dict[str, Any]]:
        """Get audio metrics for a specific session."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, timestamp, fluency_score, is_stuttering, 
                       word_count, filler_word_count, speech_rate, transcript
                FROM audio_metrics 
                WHERE session_id = ?
                ORDER BY timestamp ASC
            """, (session_id,))

            # Convert tuples to dictionaries
            columns = ["id", "timestamp", "fluency_score", "is_stuttering",
                       "word_count", "filler_word_count", "speech_rate", "transcript"]
            metrics = []

            for row in cursor.fetchall():
                metric = {}
                for i, column in enumerate(columns):
                    metric[column] = row[i]
                metrics.append(metric)

            return metrics
        except Exception as e:
            print(f"Error getting audio metrics: {e}")
            return []

    def get_posture_metrics(self, session_id: str) -> List[Dict[str, Any]]:
        """Get posture metrics for a specific session."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, timestamp, hand_detected, hand_detection_duration,
                       not_facing_camera, not_facing_duration, 
                       bad_posture_detected, bad_posture_duration
                FROM posture_metrics 
                WHERE session_id = ?
                ORDER BY timestamp ASC
            """, (session_id,))

            # Convert tuples to dictionaries
            columns = ["id", "timestamp", "hand_detected", "hand_detection_duration",
                       "not_facing_camera", "not_facing_duration",
                       "bad_posture_detected", "bad_posture_duration"]
            metrics = []

            for row in cursor.fetchall():
                metric = {}
                for i, column in enumerate(columns):
                    metric[column] = row[i]
                metrics.append(metric)

            return metrics
        except Exception as e:
            print(f"Error getting posture metrics: {e}")
            return []

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
