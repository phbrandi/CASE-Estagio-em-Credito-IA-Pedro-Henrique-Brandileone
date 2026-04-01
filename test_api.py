import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()

msg = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=100,
    messages=[{"role": "user", "content": "Responda só: API funcionando!"}]
)

print(msg.content[0].text)