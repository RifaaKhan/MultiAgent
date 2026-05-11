import os
import requests


def search_web(query: str) -> str:
    api_key = os.getenv("SERPER_API_KEY")

    if not api_key:
        return "Web search API is not configured."

    url = "https://google.serper.dev/search"

    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }

    payload = {
        "q": query,
        "num": 3,
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)

        if response.status_code != 200:
            return "Web search failed. Unable to fetch results."

        data = response.json()
        results = data.get("organic", [])

        if not results:
            return "No relevant web results found."

        output = []

        for result in results[:3]:
            output.append(
                f"Title: {result.get('title')}\n"
                f"Summary: {result.get('snippet')}\n"
                f"Link: {result.get('link')}"
            )

        return "\n\n".join(output)

    except Exception as error:
        return f"Web search failed: {error}"