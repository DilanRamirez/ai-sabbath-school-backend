import google.generativeai as genai
from typing import Literal, Dict
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


# function that returns the LLM response


def get_llm_response(prompt: str, lang: str = "es") -> Dict[str, str]:
    """
    Sends a raw prompt to the LLM and returns a dict with the 'answer' text.
    """
    if not isinstance(prompt, str) or not prompt.strip():
        logging.error("Empty or invalid prompt provided to get_llm_response.")
        return {"answer": "[Error: Prompt is empty or invalid]"}
    try:
        # prepend instruction to generate response in specified language
        prompt_with_lang = f"{prompt}\n\nPor favor, responde en {lang}."
        response = model.generate_content(prompt_with_lang)
        answer_text = getattr(response, "text", "").strip() if response else ""
        if not answer_text:
            logging.error("LLM returned an empty or invalid response.")
            return {"answer": "[Error: Invalid LLM response]"}
        return {"answer": answer_text}
    except Exception as e:
        logging.error(f"Error in get_llm_response: {e}", exc_info=True)
        return {"answer": f"[Error with LLM service: {str(e)}]"}
