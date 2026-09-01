from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class ModelTier(BaseModel):
    """Configuration for a specific model tier within an agent's cascade."""
    model: str = Field(..., description="Provider/Model string, e.g. gemini/gemini-2.5-flash")
    max_attempts: int = Field(default=1, ge=1, le=5, description="Max attempts with this model tier")

    @field_validator("model")
    @classmethod
    def validate_model_format(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Model identifier cannot be empty")
        return v


class AgentConfig(BaseModel):
    """Configuration for a specific agent in MathSolver."""
    name: str = Field(..., description="Unique agent identifier")
    description: Optional[str] = Field(default=None, description="Agent responsibility summary")
    tiers: List[ModelTier] = Field(..., min_length=1, description="Cascading model tiers in execution priority")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=8192, gt=0, description="Max output tokens")
    timeout_seconds: int = Field(default=120, gt=0, description="Timeout in seconds")
    reasoning_effort: Optional[Literal["low", "medium", "high"]] = Field(
        default=None, description="Reasoning effort for thinking models"
    )


class RetryPolicyConfig(BaseModel):
    """Global retry policy configuration."""
    retryable_errors: List[str] = Field(
        default_factory=lambda: ["rate_limit", "timeout", "connection", "server_error"]
    )
    non_retryable_errors: List[str] = Field(
        default_factory=lambda: ["invalid_request", "authentication"]
    )
    max_total_attempts: int = Field(default=5, ge=1, le=10)


class AgentModelsConfig(BaseModel):
    """Top-level agent models configuration schema."""
    version: int = Field(default=1)
    defaults: Dict[str, object] = Field(default_factory=dict)
    retry_policy: RetryPolicyConfig = Field(default_factory=RetryPolicyConfig)
    agents: Dict[str, AgentConfig] = Field(..., description="Mapping of agent names to their configurations")
