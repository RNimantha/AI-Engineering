
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.utils import load_env, header, require_key, model_use, total_usage
import anthropic
from shared.utils import load_env, header, require_key
load_env()

ANTHROPIC_MODEL = model_use("claude")

def basic_chat(user_message: str, system: str = "You are a helpful assistant.") -> str:
    """Single-turn: send one message, get one reply."""
    client = anthropic.Anthropic(api_key=require_key("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1024,
        system=system,                      
        messages=[
            {"role": "user", "content": user_message}
        ]
    )

    return  response


if __name__ == "__main__":
    print("Anthropic SDK", "Basic Chat", ANTHROPIC_MODEL)
    print("Q: What is the speed of light?")
    response = basic_chat("What is the speed of light in km/s? One sentence only.")
    print(f'Answer: {response.content[0].text}')
    print(f'input tokens: {response.usage.input_tokens}, output tokens: {response.usage.output_tokens}')
    print(f"Tokens used: {response.usage.input_tokens + response.usage.output_tokens}")
    print(f"Estimated cost of this call: ${total_usage(response):.8f}")

_response_ref = None
def _last_usage():
    return "call basic_chat() and check response.usage"
