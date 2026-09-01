import os
import yaml
import logging
from pathlib import Path
from typing import Optional, Dict
from config.schemas import AgentConfig, AgentModelsConfig

logger = logging.getLogger(__name__)

_CACHED_CONFIG: Optional[AgentModelsConfig] = None
_DEFAULT_CONFIG_PATH = Path(__file__).parent / "agent_models.yaml"


class AgentConfigResolver:
    """Resolves and validates typed AgentConfig from agent_models.yaml."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or _DEFAULT_CONFIG_PATH
        self._config: Optional[AgentModelsConfig] = None
        self._load()

    def _load(self) -> None:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Agent models config file not found: {self.config_path}")

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            # Strict validation with Pydantic
            self._config = AgentModelsConfig(**data)
            logger.info(
                f"[AgentConfigResolver] Loaded {len(self._config.agents)} agent configs from {self.config_path}"
            )
        except Exception as e:
            logger.error(f"[AgentConfigResolver] Failed to parse agent_models.yaml: {e}", exc_info=True)
            raise

    def get_agent_config(self, agent_name: str) -> AgentConfig:
        if not self._config:
            self._load()
        if not self._config or agent_name not in self._config.agents:
            # Fallback or generic agent config
            logger.warning(
                f"[AgentConfigResolver] Agent '{agent_name}' not defined in config, using defaults."
            )
            from config.schemas import ModelTier
            return AgentConfig(
                name=agent_name,
                description=f"Auto-generated fallback config for {agent_name}",
                tiers=[
                    ModelTier(model="gemini/gemini-2.5-flash", max_attempts=2),
                    ModelTier(model="gemini/gemini-2.5-pro", max_attempts=1),
                ],
                temperature=0.2,
                max_tokens=8192,
                timeout_seconds=120,
            )
        return self._config.agents[agent_name]

    @property
    def config(self) -> AgentModelsConfig:
        if not self._config:
            self._load()
        return self._config  # type: ignore


_RESOLVER_INSTANCE: Optional[AgentConfigResolver] = None


def get_agent_config_resolver() -> AgentConfigResolver:
    global _RESOLVER_INSTANCE
    if _RESOLVER_INSTANCE is None:
        _RESOLVER_INSTANCE = AgentConfigResolver()
    return _RESOLVER_INSTANCE


def load_agent_config(agent_name: str) -> AgentConfig:
    return get_agent_config_resolver().get_agent_config(agent_name)


def get_agent_models_config() -> AgentModelsConfig:
    return get_agent_config_resolver().config
