# src/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """
    Configuration class for the application.
    """
    # API Keys loaded from environment
    GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") # This can stay for now
    HF_TOKEN = os.getenv("HF_TOKEN") # Key for Hugging Face API

    # The model you want to use
    GEMINI_MODEL = "gemini-1.5-flash"

    # These values are not used in the Geoapify version but are good to keep
    PROJECT_ID = "travel-planner-ai-474206" # You can revert this if you want
    LOCATION = "us-central1"
    DEFAULT_CURRENCY = "INR"