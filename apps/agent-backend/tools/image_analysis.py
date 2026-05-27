"""Analyze images using a vision-capable model via Ollama."""
import base64
import os
from openai import AsyncOpenAI


async def analyze_image(image_path: str, query: str, client: AsyncOpenAI | None = None) -> str:
    """Analyze an image using a vision model.

    Args:
        image_path: Path to the image file.
        query: Question or prompt about the image.
        client: Optional AsyncOpenAI client (for Ollama vision).

    Returns:
        Description/analysis of the image.
    """
    if not os.path.exists(image_path):
        return f"Error: Image not found at {image_path}"

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    if client is None:
        client = AsyncOpenAI(
            base_url=os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434/v1"),
            api_key=os.getenv("LLM_API_KEY", "ollama"),
        )

    model = os.getenv("VISION_MODEL", os.getenv("LLM_CHOICE", "llama3.2"))

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": query},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64}"},
                        },
                    ],
                }
            ],
            max_tokens=2000,
            temperature=0.2,
        )
        return response.choices[0].message.content or "(no response)"
    except Exception as e:
        return f"Error analyzing image: {e}"
