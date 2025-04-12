# Career Conquer

A comprehensive career guidance and interview preparation platform that combines resume analysis, career path recommendations, and real-time body language feedback during mock interviews.

## Features

- **User Authentication**: Secure signup, login, and profile management
- **Resume Management**: Upload and analyze resumes in PDF and image formats
- **Career Guidance**: 
  - Skill identification and career path matching
  - Detailed roadmaps for career advancement
  - Personalized resume improvement tips
- **Interactive Interview Practice**:
  - Real-time body language analysis using computer vision
  - Emotion detection and feedback
  - Performance tracking and improvement suggestions

## Technical Implementation

### Backend

- **Flask**: Web framework for API endpoints and page rendering
- **SQLAlchemy**: ORM for database operations
- **MediaPipe**: Machine learning library for body language detection
- **PyMuPDF & Tesseract OCR**: PDF and image text extraction
- **scikit-learn**: Machine learning for classification tasks

### Frontend

- **HTML/CSS/JavaScript**: Responsive UI implementation
- **Webcam Integration**: Real-time video analysis during interviews

## Installation

1. Clone the repository:
```
git clone https://github.com/yourusername/career-conquer.git
cd career-conquer
```

2. Create and activate a virtual environment:
```
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```
pip install -r requirements.txt
```

4. Install Tesseract OCR:
   - **Windows**: Download and install from [Tesseract GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
   - **macOS**: `brew install tesseract`
   - **Linux**: `sudo apt install tesseract-ocr`

5. Create a `.env` file with your configuration:
```
SECRET_KEY=your_secret_key_here
```

6. Run the application:
```
python app.py
```

## Usage

1. Register an account and log in
2. Upload your resume (PDF, JPEG, or PNG format)
3. Navigate to "Career Guidance" to receive personalized career path recommendations
4. Use "Interview Practice" to rehearse with real-time body language feedback
5. Review performance and improvement suggestions

## System Requirements

- Python 3.8+
- Webcam (for interview practice)
- 4GB RAM minimum (8GB recommended)
- Modern web browser with JavaScript enabled

## Data Privacy

- All uploaded resumes are stored securely
- Video stream processing happens locally in your browser
- User data is not shared with third parties

## Troubleshooting

- **OCR Issues**: Ensure Tesseract is properly installed and available in your PATH
- **Video Feed Problems**: Check browser permissions for camera access
- **Resume Analysis Failures**: Try uploading a clearer document or in PDF format

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 