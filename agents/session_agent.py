from langchain_core.tools import tool
from llm_config import get_flash_model


@tool
def answer_from_current_chat_session(question: str, chat_history: str) -> str:
    """
    Answer user questions using only the current chat session history.
    Use this when the user asks what they asked earlier, first query,
    previous query, their name mentioned earlier, or anything from current chat.
    """
    llm = get_flash_model()

    prompt = f"""
You are a current chat session assistant.

Answer the user's question using ONLY the chat history given below.

Rules:
- Use only the current chat history.
- Do not use database memory.
- Do not invent anything.
- If the answer is not available in the chat history, say:
  "I could not find that in the current chat session."
- If the user asks for first/second/third/previous/last query,
  identify it from the user's messages in the chat history.
- If the user asks "what is my name", answer only if the user mentioned their name earlier.

Current Chat History:
{chat_history}

User Question:
{question}

Answer clearly and shortly.
"""

    response = llm.invoke(prompt)
    return response.content