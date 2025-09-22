import os
from dotenv import load_dotenv

def load_api_keys():
    """
    Loads API keys from the .env file.
    Make sure to create a .env file with your credentials.
    """
    load_dotenv()
    groq_api_key = os.getenv("GROQ_API_KEY")
    reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
    reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    reddit_user_agent = os.getenv("REDDIT_USER_AGENT")

    if not all([groq_api_key, reddit_client_id, reddit_client_secret, reddit_user_agent]):
        raise ValueError("One or more environment variables are missing. Please check your .env file.")

    return {
        "groq_api_key": groq_api_key,
        "reddit_client_id": reddit_client_id,
        "reddit_client_secret": reddit_client_secret,
        "reddit_user_agent": reddit_user_agent,
    }

# Load keys at the module level for easy access
try:
    api_keys = load_api_keys()
except ValueError as e:
    print(f"Error: {e}")
    api_keys = {}
