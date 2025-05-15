import google.generativeai as genai
from typing import Literal
import logging

from app.core.config import settings
from app.core.prompt_builder import build_prompt


# Initialize Gemini client
genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash-lite")


def generate_llm_response(
    text: str,
    mode: Literal["explain", "reflect", "apply", "summarize"],
    context_text: str,
    lang: str = "en",
) -> str:
    if not isinstance(text, str) or not text.strip():
        return "[Error: Empty or invalid input provided to LLM]"

    try:
        result = build_prompt(mode, text, context_text, lang)
        if (
            not isinstance(result, dict)
            or "prompt" not in result
            or "refs" not in result
        ):
            logging.error(
                "build_prompt did not return the expected dictionary structure."
            )
            return "[Error: Invalid prompt result structure]"

        prompt = result["prompt"]
        refs = result["refs"]

        if not isinstance(prompt, str) or not prompt.strip():
            logging.error("The prompt is empty or invalid.")
            return "[Error: Prompt generation failed]"

        response = model.generate_content(prompt)
        if not response or not hasattr(response, "text") or not response.text.strip():
            logging.error("LLM returned an empty or invalid response.")
            return "[Error: Invalid LLM response]"

        return {"answer": response.text, "refs": refs}
    except Exception as e:
        logging.error(f"Error generating LLM response: {e}")
        return f"[Error with Gemini SDK: {str(e)}]"
