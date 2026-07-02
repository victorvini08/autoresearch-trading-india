"""LLM provider abstraction.

Primary path: ClaudeCodeProvider — shells out to `claude -p PROMPT`. Uses the
locally-logged-in Claude Code session (Pro/Max subscription). No API key
needed; the cost is the user's Claude Code rate-limit budget.

Two-tier model usage:
  - Cheap/bulk classifiers (macro_regime, sentiment, events) →
    ClaudeCodeProvider(model="claude-sonnet-4-6")
  - Agentic loop driver (autoresearch meta-coder) →
    ClaudeCodeProvider(model="claude-opus-4-7")

Alternative path: CodexProvider — shells out to `codex exec PROMPT`, using
the user's OpenAI Codex subscription. Same architectural role as Claude;
gives the loop driver a second-opinion option (run two parallel sessions
on different branches for diversity). Uses --output-last-message to capture
just the final agent message, so we don't have to parse the transcript that
codex prints to stdout.

Fallback path: Qwen3OllamaProvider — stub. Local Ollama integration deferred
to a later phase; the interface exists so callers stay portable.

We use subprocess argv (not shell=True), so prompts are passed verbatim without
any shell-injection risk. Argv length limits (~128KB Linux, ~250KB macOS) are
plenty for our prompts.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


class Provider:
    """Common interface for LLM classification calls."""

    model_id: str = ""

    def classify(self, prompt: str, timeout: int = 120) -> str:
        raise NotImplementedError


class ClaudeCodeProvider(Provider):
    """Shells out to `claude -p PROMPT [--model MODEL]`.

    `model_id` is recorded in cache rows so that switching models triggers a
    clean re-classification rather than mixing outputs across versions.
    """

    model_id = "claude-code-default"  # used when no `model` is specified

    def __init__(
        self,
        claude_bin: str | None = None,
        model: str | None = None,
    ) -> None:
        self.claude_bin = claude_bin or shutil.which("claude")
        if not self.claude_bin:
            raise RuntimeError(
                "`claude` CLI not found on PATH. Install Claude Code "
                "(https://claude.com/product/claude-code) and sign in, "
                "or pass an explicit path via `claude_bin=`."
            )
        self.model = model
        if model is not None:
            self.model_id = f"claude-code-{model}"

    def classify(self, prompt: str, timeout: int = 120) -> str:
        cmd = [self.claude_bin, "-p", prompt]
        if self.model is not None:
            cmd.extend(["--model", self.model])
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"claude CLI timed out after {timeout}s") from e
        if result.returncode != 0:
            raise RuntimeError(
                f"claude CLI exit {result.returncode}: {result.stderr[:300]}"
            )
        return result.stdout.strip()


class CodexProvider(Provider):
    """Shells out to `codex exec [-m MODEL] --output-last-message FILE PROMPT`.

    Codex CLI's transcript goes to stdout (full agent loop, not what we want).
    We use `--output-last-message FILE` to capture just the final agent
    message in a tempfile, then read it back. `--color never` and
    `--skip-git-repo-check` are added for clean parseable output and to make
    the call robust regardless of where it runs.

    Default model comes from `~/.codex/config.toml` (typically `gpt-5.4` with
    `model_reasoning_effort = "high"`) when `model=None`. Pass an explicit
    `model="..."` to override.
    """

    model_id = "codex-default"

    def __init__(
        self, codex_bin: str | None = None, model: str | None = None,
    ) -> None:
        self.codex_bin = codex_bin or shutil.which("codex")
        if not self.codex_bin:
            raise RuntimeError(
                "`codex` CLI not found on PATH. Install Codex CLI and sign in "
                "with your OpenAI subscription, or pass an explicit path via "
                "`codex_bin=`."
            )
        self.model = model
        if model is not None:
            self.model_id = f"codex-{model}"

    def classify(self, prompt: str, timeout: int = 120) -> str:
        # tempfile path that codex writes the final message into
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False,
        )
        f.close()
        last_msg_path = Path(f.name)
        try:
            cmd = [
                self.codex_bin, "exec",
                "--skip-git-repo-check",
                "--color", "never",
                "--output-last-message", str(last_msg_path),
            ]
            if self.model is not None:
                cmd.extend(["-m", self.model])
            cmd.append(prompt)
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=timeout,
                )
            except subprocess.TimeoutExpired as e:
                raise RuntimeError(f"codex CLI timed out after {timeout}s") from e
            if result.returncode != 0:
                raise RuntimeError(
                    f"codex CLI exit {result.returncode}: {result.stderr[:300]}"
                )
            return last_msg_path.read_text().strip()
        finally:
            last_msg_path.unlink(missing_ok=True)


class Qwen3OllamaProvider(Provider):
    """Stub. Full Ollama integration deferred.

    When implemented this will hit `http://localhost:11434/api/generate` with
    `{"model": "qwen3-30b-a3b", "prompt": ..., "stream": false}`.
    """

    model_id = "qwen3-30b-a3b-ollama"

    def classify(self, prompt: str, timeout: int = 120) -> str:
        raise NotImplementedError(
            "Qwen3OllamaProvider is a stub; full Ollama setup deferred."
        )
