from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    llm_provider: Literal["nvidia", "local"] = "nvidia"

    # NVIDIA NIM
    nvidia_api_key: str = ""
    nvidia_model_id: str = "nvidia/nemotron-3.5-bolt-e4b"

    # Local Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model_id: str = "qwen2.5-coder:7b"

    workspace_dir: str = "./workspace"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

WORKSPACE_PATH = Path(settings.workspace_dir).resolve()
WORKSPACE_PATH.mkdir(parents=True, exist_ok=True)