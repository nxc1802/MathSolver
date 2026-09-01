import pytest
import asyncio
from typing import Tuple, Any
from config.schemas import ModelTier, AgentConfig, AgentModelsConfig
from config.loader import load_agent_config, AgentConfigResolver
from config.settings import Settings, parse_comma_separated_keys
from llm.errors import ErrorCategory, ErrorClassifier
from llm.key_state import KeyState, KeyMetadata, MemoryKeyStateStore, hash_key
from llm.key_pool import APIKeyPool
from llm.telemetry import LLMTelemetryRecord, LLMTelemetry
from agents.runtime import AgentRuntime


def test_parse_comma_separated_keys():
    raw = "key1, key2 , 'key3', \"key4\""
    keys = parse_comma_separated_keys(raw)
    assert keys == ["key1", "key2", "key3", "key4"]


def test_agent_models_config_schema_validation():
    tier1 = ModelTier(model="gemini/gemini-2.5-flash", max_attempts=2)
    tier2 = ModelTier(model="gemini/gemini-2.5-pro", max_attempts=1)
    agent = AgentConfig(
        name="test_agent",
        description="Testing agent schema",
        tiers=[tier1, tier2],
        temperature=0.1,
        max_tokens=4096,
        timeout_seconds=60,
    )
    config = AgentModelsConfig(version=1, agents={"test_agent": agent})
    assert config.version == 1
    assert "test_agent" in config.agents
    assert len(config.agents["test_agent"].tiers) == 2


def test_error_classifier():
    assert ErrorClassifier.classify(Exception("429 Too Many Requests")) == ErrorCategory.RATE_LIMIT
    assert ErrorClassifier.classify(Exception("API_KEY_INVALID: User not authorized")) == ErrorCategory.AUTH_ERROR
    assert ErrorClassifier.classify(Exception("Daily quota exceeded for project")) == ErrorCategory.QUOTA_EXHAUSTED
    assert ErrorClassifier.classify(Exception("Connection reset by peer")) == ErrorCategory.NETWORK
    assert ErrorClassifier.classify(Exception("Internal Server Error 500")) == ErrorCategory.SERVER_ERROR
    assert ErrorClassifier.classify(Exception("Request timed out")) == ErrorCategory.TIMEOUT


@pytest.mark.asyncio
async def test_key_pool_round_robin_and_cooldown():
    store = MemoryKeyStateStore()
    pool = APIKeyPool(state_store=store)
    custom_prov = "test_custom_prov"
    pool.register_keys(custom_prov, ["key_alpha", "key_beta", "key_gamma"])

    # First rotation
    k1, h1 = await pool.get_next_key(custom_prov)
    k2, h2 = await pool.get_next_key(custom_prov)
    k3, h3 = await pool.get_next_key(custom_prov)

    assert [k1, k2, k3] == ["key_alpha", "key_beta", "key_gamma"]

    # Put key_alpha on cooldown
    await pool.mark_cooldown("key_alpha", retry_after=120)

    # Next key should skip key_alpha
    k_next, _ = await pool.get_next_key(custom_prov)
    assert k_next in ("key_beta", "key_gamma")


@pytest.mark.asyncio
async def test_agent_runtime_validator_cascade():
    """Simulates Tier 1 (flash) failing validation and Tier 2 (pro) succeeding validation on analyzer."""
    call_history = []

    class MockLLMService:
        async def acomplete(self, model: str, messages: list, **kwargs) -> str:
            call_history.append(model)
            if "flash" in model:
                return "INVALID_OUTPUT_FROM_TIER_1"
            return '{"type": "pyramid", "analysis": "Valid analysis from Tier 2"}'

    runtime = AgentRuntime(llm_service=MockLLMService())

    def mock_validator(raw_output: str) -> Tuple[bool, Any]:
        if "INVALID" in raw_output:
            return False, "Malformed analysis output"
        return True, {"valid": True, "raw": raw_output}

    messages = [{"role": "user", "content": "Analyze problem"}]
    res = await runtime.run(
        agent="input_analyzer",
        messages=messages,
        validator=mock_validator,
    )

    assert res["valid"] is True
    # Verify that Tier 1 (flash) was attempted and escalated to Tier 2 (pro)
    assert any("flash" in m for m in call_history)
    assert any("pro" in m for m in call_history)
