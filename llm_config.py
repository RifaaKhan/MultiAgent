import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

load_dotenv()


def get_env_value(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Missing environment variable: {key}")
    return value


def get_provider() -> str:
    return os.getenv("LLM_PROVIDER", "gemini").lower()


def get_gemini_model(model_env_key: str, default_model: str, temperature: float):
    return ChatGoogleGenerativeAI(
        model=os.getenv(model_env_key, default_model),
        google_api_key=get_env_value("GEMINI_API_KEY"),
        temperature=temperature,
    )


def get_groq_model(model_env_key: str, default_model: str, temperature: float):
    return ChatGroq(
        model=os.getenv(model_env_key, default_model),
        groq_api_key=get_env_value("GROQ_API_KEY"),
        temperature=temperature,
    )


def get_flash_model():
    if get_provider() == "groq":
        return get_groq_model("GROQ_FAST_MODEL", "llama-3.1-8b-instant", 0.2)

    return get_gemini_model("GEMINI_FLASH_MODEL", "gemini-2.5-flash", 0.2)


def get_pro_model():
    if get_provider() == "groq":
        return get_groq_model("GROQ_REASONING_MODEL", "llama-3.1-8b-instant", 0.3)

    return get_gemini_model("GEMINI_PRO_MODEL", "gemini-2.5-flash-lite", 0.3)


def test_models():
    flash = get_flash_model()
    pro = get_pro_model()

    flash_response = flash.invoke(
        "Classify this user intent in one word: I want to apply leave tomorrow."
    )

    pro_response = pro.invoke(
        "Explain in two simple lines why RAG is useful in an enterprise chatbot."
    )

    print("\nFast Model Response:")
    print(flash_response.content)

    print("\nReasoning Model Response:")
    print(pro_response.content)


if __name__ == "__main__":
    test_models()