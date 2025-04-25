"""
Integration functions for the Interview Advisor

This module provides integration functions for connecting the Interview Advisor
with the main site.
"""

import os
from typing import List, Optional

# Path to resume files
# RESUME_DIR = "uploads/resumes" # Original incorrect path
RESUME_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'uploads') # Path relative to project root


def mainmenu() -> List[str]:
    """
    Return the main menu options as a list of strings.

    Returns:
        List[str]: A list of menu option strings
    """
    menu_options = [
        "Upload Resume",
        "Start Interview",
        "Process Interview Answer",
        "End Interview & Get Recommendations",
        "Resume Analysis",
        "Change TTS Voice",
        "Test Audio",
        "Configure Speech Input",
        "Exit"
    ]
    return menu_options


def get_menu_options() -> List[dict]:
    """
    Return the main menu options as a list of dictionaries, suitable for structured use.

    Each dictionary contains:
        - text (str): The display text for the menu option.
        - action_id (str): The identifier (typically the original menu number) for the action.

    Returns:
        List[dict]: A list of menu option dictionaries.
    """
    menu_items = mainmenu() # Get the original list
    options = []
    for i, item in enumerate(menu_items, 1):
        options.append({"text": item, "action_id": str(i)})
    return options


def getresumesir() -> str:
    """
    Get the path to the resume directory where resume files are stored.

    Returns:
        str: Path to the resume directory
    """
    # Ensure the resume directory exists
    if not os.path.exists(RESUME_DIR):
        os.makedirs(RESUME_DIR, exist_ok=True)

    return RESUME_DIR


def get_resume_path(resume_id: str) -> Optional[str]:
    """
    Get the full path to a specific resume file.

    Args:
        resume_id (str): The ID or filename of the resume

    Returns:
        Optional[str]: The full path to the resume file, or None if not found
    """
    resume_path = os.path.join(RESUME_DIR, resume_id)

    if os.path.exists(resume_path):
        return resume_path

    return None


def list_available_resumes() -> List[str]:
    """
    List all available resume files in the resume directory.

    Returns:
        List[str]: A list of resume filenames
    """
    if not os.path.exists(RESUME_DIR):
        return []

    return [f for f in os.listdir(RESUME_DIR) if os.path.isfile(os.path.join(RESUME_DIR, f))]
