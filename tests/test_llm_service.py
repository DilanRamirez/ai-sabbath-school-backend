import pytest
from unittest.mock import patch, MagicMock
from app.services.llm_service import generate_llm_response
from app.core.prompt_builder import build_prompt


def test_build_prompt_explain_english():
    question = "Isaiah 53:5"
    context = "Isaiah 53:5"
    prompt = build_prompt("explain", question, context, lang="en")
    prompt = prompt if isinstance(prompt, str) else prompt.get("prompt", prompt)
    # Should include both question and context
    assert isinstance(prompt, str)
    assert question in prompt
    assert context in prompt


def test_build_prompt_reflect_spanish():
    question = "Juan 3:16"
    context = "Juan 3:16"
    prompt = build_prompt("reflect", question, context, lang="es")
    prompt = prompt if isinstance(prompt, str) else prompt.get("prompt", prompt)
    # Should include both question and context
    assert isinstance(prompt, str)
    assert question in prompt
    assert context in prompt


# --- TEST generate_llm_response ---
@patch("app.services.llm_service.model.generate_content")
def test_generate_llm_response_valid(mock_generate):
    mock_generate.return_value = MagicMock(text="Jesus died for our sins.")
    result = generate_llm_response("Isaiah 53:5", "explain", "en")
    assert isinstance(result, dict)
    assert "Jesus" in result["answer"]


@patch("app.services.llm_service.model.generate_content")
def test_generate_llm_response_spanish(mock_generate):
    mock_generate.return_value = MagicMock(text="Jesús murió por nuestros pecados.")
    result = generate_llm_response("Isaías 53:5", "explain", "es")
    assert "Jesús" in result["answer"]


@patch("app.services.llm_service.model.generate_content")
def test_generate_llm_response_error_handling(mock_generate):
    mock_generate.side_effect = Exception("Gemini is down")
    result = generate_llm_response("Isaiah 53:5", "reflect", "en")
    assert result.startswith("[Error with Gemini SDK:")


def test_build_prompt_ask_mode():
    question = "¿Qué es el santuario?"
    context = question
    prompt = build_prompt("ask", question, context, lang="es")
    assert "Pregunta" in prompt["prompt"] or "¿Qué es el santuario?" in prompt["prompt"]


@patch("app.services.llm_service.model.generate_content")
def test_generate_llm_response_empty_input(mock_generate):
    mock_generate.return_value = MagicMock(text="I'm sorry, I need more context.")
    result = generate_llm_response("", "ask", "en")
    print(result)
    answer = result["answer"] if isinstance(result, dict) else result
    # Empty input triggers the guard-clause error
    expected = "[error: empty or invalid input provided to llm]"
    assert answer.lower().startswith(expected)
