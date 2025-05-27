import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """
    Configuration class for the agentic blog writer application.

    This class loads configuration settings from environment variables,
    typically defined in a .env file at the root of the project.

    Usage:
    1. Ensure you have a .env file with necessary API keys and model preferences.
       Example .env content:
       OPENAI_API_KEY="your_openai_api_key"
       GEMINI_API_KEY="your_gemini_api_key"
       LARGE_REASONING_MODEL="gpt-4o"
       # ... and other settings

    2. Import the global `config` instance from this module:
       `from app.core.config import config`

    3. Access configuration values as attributes:
       `api_key = config.OPENAI_API_KEY`
       `model = config.LARGE_REASONING_MODEL`

    4. To validate required configurations (e.g., API keys) at startup:
       `Config.validate_config()`
       This will raise a ValueError if required keys are missing.

    5. To get a dictionary of all model configurations:
       `model_settings = Config.get_model_config()`
    """
    
    # API Keys
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    
    # Model configurations
    LARGE_REASONING_MODEL: str = os.getenv("LARGE_REASONING_MODEL")
    SMALL_REASONING_MODEL: str = os.getenv("SMALL_REASONING_MODEL")
    SMALL_FAST_MODEL: str = os.getenv("SMALL_FAST_MODEL")
    LARGE_FAST_MODEL: str = os.getenv("LARGE_FAST_MODEL")
    IMAGE_GENERATION_MODEL: str = os.getenv("IMAGE_GENERATION_MODEL")
    
    # Logging
    LOGGING_LEVEL: str = os.getenv("LOGGING_LEVEL")
    
    # API Keys
    FIRECRAWL_API_KEY: Optional[str] = os.getenv("FIRECRAWL_API_KEY")
    
    def __init__(self):
        self.validate_config()

    @classmethod
    def validate_config(cls) -> bool:
        """Validate that required configuration is present."""
        required_keys = ["OPENAI_API_KEY"]
        missing_keys = []
        
        for key in required_keys:
            if not getattr(cls, key):
                missing_keys.append(key)
        
        if missing_keys:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_keys)}")
        
        return True
    
    @classmethod
    def get_model_config(cls) -> dict:
        """Get all model configurations as a dictionary."""
        return {
            "large_reasoning": cls.LARGE_REASONING_MODEL,
            "small_reasoning": cls.SMALL_REASONING_MODEL,
            "small_fast": cls.SMALL_FAST_MODEL,
            "large_fast": cls.LARGE_FAST_MODEL,
            "image_generation": cls.IMAGE_GENERATION_MODEL,
            "logging_level": cls.LOGGING_LEVEL,
        }


# Create a global config instance
config = Config()