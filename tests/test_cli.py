from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from app import __version__
from app.ai.model_client import GenerateResult
from app.cli import app
from app.core.errors import ProviderError

runner = CliRunner()


def test_version_command_prints_package_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_help_lists_all_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("version", "models", "ask", "chat", "serve"):
        assert cmd in result.stdout


def test_models_shows_provider_without_secrets():
    result = runner.invoke(app, ["models"])
    assert result.exit_code == 0
    assert "ollama" in result.stdout
    assert "qwen3:8b" in result.stdout
    assert "api_key" not in result.stdout


@patch(
    "app.ai.providers.openai_compatible.OpenAICompatibleModelClient.generate",
    new=AsyncMock(return_value=GenerateResult(content="42", provider="fake", model="fake-model")),
)
def test_ask_command_prints_answer():
    result = runner.invoke(app, ["ask", "what is 6 times 7?", "--plain"])
    assert result.exit_code == 0
    assert "42" in result.stdout


@patch(
    "app.ai.providers.openai_compatible.OpenAICompatibleModelClient.generate",
    new=AsyncMock(side_effect=ProviderError.timeout()),
)
def test_ask_command_provider_error_exits_nonzero():
    result = runner.invoke(app, ["ask", "anything"])
    assert result.exit_code == 2
    # Error envelope details go to stderr; mixed_stderr=True is default in CliRunner
    # Typer prints the error via err_console; we just verify non-zero exit.


def test_ask_validation_error_on_negative_max_tokens():
    result = runner.invoke(app, ["ask", "hi", "--max-tokens", "-1"])
    assert result.exit_code != 0


@patch(
    "app.ai.providers.openai_compatible.OpenAICompatibleModelClient.generate",
    new=AsyncMock(
        return_value=GenerateResult(content="hello", provider="fake", model="fake-model")
    ),
)
def test_chat_command_handles_eof_immediately():
    # Send empty stdin → Prompt.ask raises EOFError on first read → loop exits cleanly.
    result = runner.invoke(app, ["chat"], input="")
    assert result.exit_code == 0


@patch(
    "app.ai.providers.openai_compatible.OpenAICompatibleModelClient.generate",
    new=AsyncMock(
        return_value=GenerateResult(content="hi there", provider="fake", model="fake-model")
    ),
)
def test_chat_command_one_turn_then_exit():
    # Two lines: a question, then 'exit'. Newline-terminated.
    result = runner.invoke(app, ["chat"], input="hello\nexit\n")
    assert result.exit_code == 0
    assert "hi there" in result.stdout
