"""
Database models for the Interview Advisor application
"""

import os
import time
import sqlite3
from typing import Dict, List, Any, Optional


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
                    metrics.get("timestamp", time.time()),
                    metrics.get("fluency_score", 0),
                    1 if metrics.get("is_stuttering", False) else 0,
                    metrics.get("word_count", 0),
                    metrics.get("filler_word_count", 0),
                    metrics.get("speech_rate", 0),
                    metrics.get("transcript", "")
                )
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saving audio metrics: {e}")
            return False

    def save_posture_metrics(self, session_id: str, metrics: Dict[str, Any]) -> bool:
        """Save posture metrics."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT INTO posture_metrics 
                   (session_id, timestamp, hand_detected, hand_detection_duration,
                    not_facing_camera, not_facing_duration, bad_posture_detected,
                    bad_posture_duration)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    metrics.get("timestamp", time.time()),
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
            cursor = self.conn.cursor()

            # Convert lists to JSON strings if needed
            import json
            strengths = json.dumps(analysis.get("strengths", []))
            areas_for_improvement = json.dumps(
                analysis.get("areas_for_improvement", []))
            recommendations = json.dumps(analysis.get("recommendations", []))

            cursor.execute(
                """INSERT INTO interview_analysis
                   (session_id, strengths, areas_for_improvement,
                    communication_rating, technical_rating, recommendations)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    strengths,
                    areas_for_improvement,
                    str(analysis.get("communication_rating", 0)),
                    str(analysis.get("technical_rating", 0)),
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
            # Get session details
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            session_data = cursor.fetchone()

            if not session_data:
                return {"error": "Session not found"}

            session_cols = [col[0] for col in cursor.description]
            session_dict = dict(zip(session_cols, session_data))

            # Get audio metrics
            cursor.execute(
                "SELECT * FROM audio_metrics WHERE session_id = ? ORDER BY timestamp",
                (session_id,)
            )
            audio_data = cursor.fetchall()
            audio_cols = [col[0] for col in cursor.description]
            audio_metrics = [dict(zip(audio_cols, row)) for row in audio_data]

            # Get posture metrics
            cursor.execute(
                "SELECT * FROM posture_metrics WHERE session_id = ? ORDER BY timestamp",
                (session_id,)
            )
            posture_data = cursor.fetchall()
            posture_cols = [col[0] for col in cursor.description]
            posture_metrics = [dict(zip(posture_cols, row))
                               for row in posture_data]

            # Get analysis results
            cursor.execute(
                "SELECT * FROM interview_analysis WHERE session_id = ?",
                (session_id,)
            )
            analysis_data = cursor.fetchone()
            analysis_dict = {}

            if analysis_data:
                analysis_cols = [col[0] for col in cursor.description]
                analysis_dict = dict(zip(analysis_cols, analysis_data))

                # Parse JSON strings back to lists
                import json
                for field in ["strengths", "areas_for_improvement", "recommendations"]:
                    if field in analysis_dict and analysis_dict[field]:
                        try:
                            analysis_dict[field] = json.loads(
                                analysis_dict[field])
                        except:
                            analysis_dict[field] = []

            # Combine all data
            result = {
                "session": session_dict,
                "audio_metrics": audio_metrics,
                "posture_metrics": posture_metrics,
                "analysis": analysis_dict
            }

            return result
        except Exception as e:
            print(f"Error getting session metrics: {e}")
            return {"error": str(e)}

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Get a list of all sessions."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions ORDER BY start_time DESC"
            )
            sessions_data = cursor.fetchall()

            if not sessions_data:
                return []

            session_cols = [col[0] for col in cursor.description]
            sessions = []

            for row in sessions_data:
                session_dict = dict(zip(session_cols, row))
                sessions.append(session_dict)

            return sessions
        except Exception as e:
            print(f"Error getting all sessions: {e}")
            return []

    def get_session_details(self, session_id: str) -> Dict[str, Any]:
        """Get details for a specific session."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            session_data = cursor.fetchone()

            if not session_data:
                return {"error": "Session not found"}

            session_cols = [col[0] for col in cursor.description]
            session_dict = dict(zip(session_cols, session_data))

            # Get analysis results
            cursor.execute(
                "SELECT * FROM interview_analysis WHERE session_id = ?",
                (session_id,)
            )
            analysis_data = cursor.fetchone()

            if analysis_data:
                analysis_cols = [col[0] for col in cursor.description]
                analysis_dict = dict(zip(analysis_cols, analysis_data))

                # Parse JSON strings back to lists
                import json
                for field in ["strengths", "areas_for_improvement", "recommendations"]:
                    if field in analysis_dict and analysis_dict[field]:
                        try:
                            analysis_dict[field] = json.loads(
                                analysis_dict[field])
                        except:
                            analysis_dict[field] = []

                session_dict["analysis"] = analysis_dict

            # Get metrics counts
            cursor.execute(
                "SELECT COUNT(*) FROM audio_metrics WHERE session_id = ?",
                (session_id,)
            )
            audio_count = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM posture_metrics WHERE session_id = ?",
                (session_id,)
            )
            posture_count = cursor.fetchone()[0]

            session_dict["audio_metrics_count"] = audio_count
            session_dict["posture_metrics_count"] = posture_count

            return session_dict
        except Exception as e:
            print(f"Error getting session details: {e}")
            return {"error": str(e)}

    def get_audio_metrics(self, session_id: str) -> List[Dict[str, Any]]:
        """Get audio metrics for a specific session."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM audio_metrics WHERE session_id = ? ORDER BY timestamp",
                (session_id,)
            )
            metrics_data = cursor.fetchall()

            if not metrics_data:
                return []

            metrics_cols = [col[0] for col in cursor.description]
            metrics = []

            for row in metrics_data:
                metrics_dict = dict(zip(metrics_cols, row))
                # Convert boolean fields
                metrics_dict["is_stuttering"] = bool(
                    metrics_dict["is_stuttering"])
                metrics.append(metrics_dict)

            return metrics
        except Exception as e:
            print(f"Error getting audio metrics: {e}")
            return []

    def get_posture_metrics(self, session_id: str) -> List[Dict[str, Any]]:
        """Get posture metrics for a specific session."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM posture_metrics WHERE session_id = ? ORDER BY timestamp",
                (session_id,)
            )
            metrics_data = cursor.fetchall()

            if not metrics_data:
                return []

            metrics_cols = [col[0] for col in cursor.description]
            metrics = []

            for row in metrics_data:
                metrics_dict = dict(zip(metrics_cols, row))
                # Convert boolean fields
                for field in ["hand_detected", "not_facing_camera", "bad_posture_detected"]:
                    metrics_dict[field] = bool(metrics_dict[field])
                metrics.append(metrics_dict)

            return metrics
        except Exception as e:
            print(f"Error getting posture metrics: {e}")
            return []

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
