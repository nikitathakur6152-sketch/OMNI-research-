from mistralai import Mistral
from app.config import MISTRAL_API_KEY, MISTRAL_MODEL

def chat(system_prompt: str, user_prompt: str) -> str:
    if not MISTRAL_API_KEY:
        raise RuntimeError("MISTRAL_API_KEY is missing in backend/.env")
    client = Mistral(api_key=MISTRAL_API_KEY)
    response = client.chat.complete(
        model=MISTRAL_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    content = response.choices[0].message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(getattr(x, "text", str(x)) for x in content)
    return str(content)
