from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import os


class Settings(BaseSettings):
    # API Configuration
    api_version: str = Field(default="v1", env="API_VERSION")
    api_port: int = Field(default=8000, env="API_PORT")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    
    # API Keys
    groq_api_key: str = Field(..., env="GROQ_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    
    # AWS Configuration
    aws_region: str = Field(default="us-east-1", env="AWS_REGION")
    aws_access_key_id: Optional[str] = Field(None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(None, env="AWS_SECRET_ACCESS_KEY")
    
    # Database Configuration
    dynamodb_endpoint: Optional[str] = Field(None, env="DYNAMODB_ENDPOINT")
    dynamodb_conversations_table: str = Field(default="ConversationState", env="DYNAMODB_CONVERSATIONS_TABLE")
    dynamodb_profiles_table: str = Field(default="UserProfiles", env="DYNAMODB_PROFILES_TABLE")
    elasticsearch_url: str = Field(default="http://localhost:9200", env="ELASTICSEARCH_URL")
    elasticsearch_api_key: Optional[str] = Field(None, env="ELASTICSEARCH_API_KEY")
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Security
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=1440, env="JWT_EXPIRATION_MINUTES")
    
    # WebSocket Configuration
    ws_heartbeat_interval: int = Field(default=30, env="WS_HEARTBEAT_INTERVAL")
    ws_connection_timeout: int = Field(default=300, env="WS_CONNECTION_TIMEOUT")
    
    # Monitoring
    sentry_dsn: Optional[str] = Field(None, env="SENTRY_DSN")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    
    # Therapeutic Engine Configuration
    max_distress_score: int = 10
    crisis_threshold: int = 8
    low_engagement_threshold: int = 3
    alliance_falter_threshold: int = 4
    
    # Memory Configuration
    conversation_ttl_days: int = 90
    user_profile_ttl_days: int = 180
    max_summary_turns: int = 10
    
    # Model Configuration
    listener_model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"
    advisor_model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"
    emotion_model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"
    signal_extract_model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"
    alliance_model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"
    safety_model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"
    
    # CORS Configuration
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


settings = Settings()