from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    anthropic_api_key: str = ""
    ollama_model: str = "minimax-m2.5:cloud"
    ollama_host: str = "http://localhost:11434"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
