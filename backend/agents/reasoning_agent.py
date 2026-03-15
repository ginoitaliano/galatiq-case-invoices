from langchain_openai import ChatOpenAI
from config import settings
from utils.llm_utils import invoke_llm  

def get_llm():
    return ChatOpenAI(
        model="meta-llama/Llama-3.3-70B-Instruct",  
        base_url="https://lightning.ai/api/v1/",
        api_key=f"{settings.lightning_api_key}/ginoitaliano/experiment-lifecycle-project"
    )

# lazy — only created when first called
_llm = None

def call_llm(persona: str, user_message: str) -> str:
    global _llm
    if _llm is None:
        _llm = get_llm()
    return invoke_llm(_llm, persona, user_message)