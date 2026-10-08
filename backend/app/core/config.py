from pathlib import Path
import os
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    project_root: Path = ROOT
    cors_origins: list[str] = ['http://localhost:3000', 'http://127.0.0.1:3000']
    allow_experimental_search: bool = False
    enable_generation: bool = False
    deepseek_api_key: SecretStr = SecretStr('')
    deepseek_model: str = Field(default='deepseek-flash', min_length=1, max_length=100, pattern=r'^[A-Za-z0-9._/-]+$')
    provider_timeout_seconds: float = Field(default=30, ge=1, le=120)
    max_output_tokens: int = Field(default=900, ge=100, le=2000)
    max_prompt_bytes: int = Field(default=16000, ge=4000, le=32000)
    max_context_chars: int = Field(default=6000, ge=500, le=10000)
    generation_calls_per_minute: int = Field(default=5, ge=1, le=30)
    max_request_bytes: int = Field(default=32768, ge=8192, le=65536)

    @field_validator('cors_origins')
    @classmethod
    def exact_origins(cls, values):
        if any(v == '*' or not v.startswith(('http://', 'https://')) or v.rstrip('/') != v for v in values):
            raise ValueError('Use exact HTTP(S) origins without trailing slashes or wildcard')
        return values

    @classmethod
    def from_env(cls):
        # Read only known settings. Never print dotenv contents or real API keys.
        environment = {**dotenv_values(ROOT / '.env'), **os.environ}
        names = {
            'RUYA_PROJECT_ROOT': 'project_root', 'RUYA_ALLOW_EXPERIMENTAL_SEARCH': 'allow_experimental_search',
            'RUYA_ENABLE_GENERATION': 'enable_generation', 'DEEPSEEK_API_KEY': 'deepseek_api_key',
            'DEEPSEEK_MODEL': 'deepseek_model', 'RUYA_PROVIDER_TIMEOUT_SECONDS': 'provider_timeout_seconds',
            'RUYA_MAX_OUTPUT_TOKENS': 'max_output_tokens', 'RUYA_MAX_PROMPT_BYTES': 'max_prompt_bytes',
            'RUYA_MAX_CONTEXT_CHARS': 'max_context_chars', 'RUYA_GENERATION_CALLS_PER_MINUTE': 'generation_calls_per_minute',
        }
        values = {field: environment[name] for name, field in names.items() if environment.get(name) not in (None, '')}
        if 'RUYA_CORS_ORIGINS' in environment:
            values['cors_origins'] = [v.strip() for v in environment['RUYA_CORS_ORIGINS'].split(',') if v.strip()]
        return cls.model_validate(values)
