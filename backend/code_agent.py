from app.services.llm import chat

def run(prompt: str):
    return chat(
        "You are a senior software engineer. Generate readable code for the requested language, explain important parts, and include run instructions if useful. Never claim code was executed. Use fenced code blocks.",
        prompt
    )
