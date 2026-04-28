from pathlib import Path
from typing import List, Dict

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from llm_config import get_pro_model

DATA_DIR = Path("data")
CHROMA_DIR = Path("data/chroma_db")
COLLECTION_NAME = "enterprise_policy_knowledge"


embedding_function = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)


def read_policy_files() -> List[Dict]:
    """
    Reads all .txt policy files from data folder.
    This keeps the system dynamic because we do not hardcode each policy file.
    """
    documents = []

    for file_path in DATA_DIR.glob("*.txt"):
        text = file_path.read_text(encoding="utf-8").strip()

        if text:
            documents.append({
                "source": file_path.name,
                "text": text
            })

    return documents


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> List[str]:
    """
    Splits long documents into smaller chunks.
    Chunking improves retrieval accuracy.
    """
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start = end - overlap

    return chunks


def get_collection():
    """
    Creates or loads ChromaDB collection.
    ChromaDB stores document chunks and helps search relevant policy content.
    """
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function
    )


def build_vector_store() -> str:
    """
    Loads policy files, chunks them, and stores them in ChromaDB.
    Rebuilds the collection so updated policy files are reflected.
    """
    documents = read_policy_files()
    collection = get_collection()

    existing = collection.get()
    if existing and existing.get("ids"):
        collection.delete(ids=existing["ids"])

    ids = []
    texts = []
    metadatas = []

    for doc in documents:
        source = doc["source"]
        chunks = chunk_text(doc["text"])

        for index, chunk in enumerate(chunks):
            ids.append(f"{source}-{index}")
            texts.append(chunk)
            metadatas.append({
                "source": source,
                "chunk_index": index
            })

    if not texts:
        return "No policy documents found."

    collection.add(
        ids=ids,
        documents=texts,
        metadatas=metadatas
    )

    return f"Vector store created successfully with {len(texts)} chunks."


def retrieve_policy_context(question: str, top_k: int = 3) -> Dict:
    """
    Retrieves top matching chunks from ChromaDB for the user question.
    """
    collection = get_collection()

    results = collection.query(
        query_texts=[question],
        n_results=top_k
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    if not documents:
        return {
            "context": "",
            "sources": []
        }

    sources = []
    context_parts = []

    for doc, metadata in zip(documents, metadatas):
        source = metadata.get("source", "unknown")

        # Simple relevance filter (optional but helpful)
        if len(doc.strip()) < 30:
            continue

        sources.append(source)
        context_parts.append(f"Source: {source}\nContent: {doc}")

    return {
        "context": "\n\n".join(context_parts),
        "sources": sorted(set(sources))
    }


def ask_policy_question(question: str) -> str:
    """
    Retrieves policy context and asks Gemini to generate a clean answer.
    """
    retrieved = retrieve_policy_context(question)

    if not retrieved["context"]:
        return "I could not find relevant information in the policy documents."

    llm = get_pro_model()

    prompt = f"""
You are an internal enterprise HR and IT policy assistant.

Answer the user's question using ONLY the policy context provided below.
Do not invent information.
If the answer is not available in the context, say:
"I could not find this information in the available policy documents."

User question:
{question}

Policy context:
{retrieved["context"]}

Instructions:
- Give a clear and short answer.
- Mention the source file name at the end.
- Do not include unrelated policy details.
"""

    response = llm.invoke(prompt)

    sources = ", ".join(sorted(set(retrieved["sources"])))

    clean_answer = response.content.split("Source:")[0].strip()
    return f"{clean_answer}\n\nSource: {sources}"


def run_tests():
    print("\nBuilding vector store...")
    print(build_vector_store())

    print("\nTesting RAG with LLM...")
    question = "What is the notice period?"
    print(f"\nQuestion: {question}")
    print(ask_policy_question(question))

    question = "Biryani Recipe?"
    print(f"\nQuestion: {question}")
    print(ask_policy_question(question))


if __name__ == "__main__":
    run_tests()