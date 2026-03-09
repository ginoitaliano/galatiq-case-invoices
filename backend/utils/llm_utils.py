# backend/utils/llm_utils.py
import time
import logging
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


def invoke_llm(llm, persona: str, user_message: str, retries: int = 3) -> str:
    """
    Send a message to any LLM with a specific persona.
    Includes exponential backoff retry for rate limits and transient errors.

    Args:
        llm: the LangChain LLM instance
        persona: system prompt defining task context and criteria
        user_message: the actual content to reason about
        retries: number of retry attempts before raising (default 3)

    Returns:
        str: the LLM's response text, stripped of whitespace
    """
    messages = [
        SystemMessage(content=persona),
        HumanMessage(content=user_message)
    ]

    for attempt in range(retries):
        try:
            response = llm.invoke(messages)
            return response.content.strip()
        except Exception as e:
            is_last = attempt == retries - 1
            wait = 2 ** attempt  

            if "credit balance" in str(e) or "401" in str(e):
                logger.error(f"LLM auth/billing error, not retrying: {e}")
                raise

            if is_last:
                logger.error(f"LLM call failed after {retries} attempts: {e}")
                raise

            logger.warning(f"LLM call failed (attempt {attempt + 1}/{retries}), retrying in {wait}s: {e}")
            time.sleep(wait)