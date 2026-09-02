import inspect
import logging
from typing import List, Dict, Any, Optional, Callable, Tuple, Union
from config.loader import load_agent_config
from config.schemas import AgentConfig
from llm.service import LLMService, get_llm_service

logger = logging.getLogger(__name__)


class AgentRuntime:
    """
    Agent Runtime & Cascading Controller:
    Coordinates agent configuration resolution, model tier escalation, and programmatic validation.
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or get_llm_service()

    async def run(
        self,
        agent: str,
        messages: List[Dict[str, Any]],
        validator: Optional[Callable[[str], Union[Tuple[bool, Any], Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """
        Executes an agent run across tiered model cascades with validator-guided escalation.
        Temperature and max_tokens are always resolved from AgentConfig (single source of truth).
        """
        config: AgentConfig = load_agent_config(agent)
        temperature = config.temperature
        max_tokens = config.max_tokens

        last_error = None
        current_messages = list(messages)

        logger.info(f"[AgentRuntime] Starting run for agent '{agent}' with {len(config.tiers)} tier(s)...")

        for tier_idx, tier in enumerate(config.tiers, start=1):
            for attempt in range(tier.max_attempts):
                logger.info(
                    f"[AgentRuntime] Agent '{agent}' Tier {tier_idx}/{len(config.tiers)} "
                    f"({tier.model}) - Attempt {attempt + 1}/{tier.max_attempts}"
                )

                try:
                    tier_reasoning_effort = tier.reasoning_effort if tier.reasoning_effort is not None else config.reasoning_effort
                    raw_output = await self.llm_service.acomplete(
                        model=tier.model,
                        messages=current_messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout=config.timeout_seconds,
                        response_format=response_format,
                        reasoning_effort=tier_reasoning_effort,
                        agent_name=agent,
                        tier_index=tier_idx,
                        **kwargs
                    )

                    # Programmatic validation (Level 2 Cascade Trigger)
                    if validator:
                        try:
                            if inspect.iscoroutinefunction(validator):
                                val_result = await validator(raw_output)
                            else:
                                val_result = validator(raw_output)

                            # Expect (is_valid, payload_or_error)
                            if isinstance(val_result, tuple) and len(val_result) == 2:
                                is_valid, payload = val_result
                                if is_valid:
                                    logger.info(
                                        f"[AgentRuntime] Agent '{agent}' Tier {tier_idx} validation PASSED."
                                    )
                                    return payload
                                else:
                                    logger.warning(
                                        f"[AgentRuntime] Agent '{agent}' Tier {tier_idx} validation FAILED: {payload}. "
                                        "Escalating..."
                                    )
                                    # Provide feedback to conversation context for subsequent attempts
                                    current_messages.append({"role": "assistant", "content": raw_output})
                                    current_messages.append({
                                        "role": "user",
                                        "content": f"Your previous output failed validation: {payload}. Please correct the issues and provide a valid response."
                                    })
                                    continue
                            elif bool(val_result):
                                return val_result
                        except Exception as val_e:
                            logger.warning(
                                f"[AgentRuntime] Validator raised exception on Tier {tier_idx}: {val_e}. Escalating..."
                            )
                            last_error = val_e
                            continue
                    else:
                        # No validator required, output is accepted
                        return raw_output

                except Exception as tier_e:
                    logger.warning(
                        f"[AgentRuntime] Tier {tier_idx} attempt {attempt + 1} failed: {tier_e}"
                    )
                    last_error = tier_e

        # All model tiers exhausted
        raise RuntimeError(
            f"Agent '{agent}' cascade exhausted all {len(config.tiers)} model tiers. Last error: {last_error}"
        )


_GLOBAL_AGENT_RUNTIME: Optional[AgentRuntime] = None


def get_agent_runtime() -> AgentRuntime:
    global _GLOBAL_AGENT_RUNTIME
    if _GLOBAL_AGENT_RUNTIME is None:
        _GLOBAL_AGENT_RUNTIME = AgentRuntime()
    return _GLOBAL_AGENT_RUNTIME
