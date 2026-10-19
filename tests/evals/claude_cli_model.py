"""DeepEval model adapter for the Claude CLI."""

import json

from deepeval.models import DeepEvalBaseLLM

from tests.evals.custom_llm_judge import claude_cli_generate


class ClaudeCLIModel(DeepEvalBaseLLM):
    """Use the Claude CLI as a DeepEval evaluator."""

    def __init__(self, model: str = "sonnet"):
        self.model = model

    def load_model(self):
        """Return the CLI model identifier."""
        return self.model

    def generate(self, prompt: str, schema=None, **kwargs):
        """Generate text or a structured Pydantic response."""
        if schema is not None:
            prompt += "\n\nReturn only a valid JSON object matching this schema:\n" + json.dumps(
                schema.model_json_schema()
            )

        response = claude_cli_generate(prompt, model=self.model)

        if schema is not None:
            return schema.model_validate_json(response)

        return response

    async def a_generate(self, prompt: str, schema=None, **kwargs):
        """Generate through the synchronous Claude CLI."""
        return self.generate(prompt, schema=schema, **kwargs)

    def get_model_name(self) -> str:
        """Return the evaluator model name."""
        return f"claude-cli-{self.model}"
