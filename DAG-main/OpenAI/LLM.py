from openai import OpenAI
from openai_prompts import (
    NODE_RESPONSE_SCHEMA,
    ANSWER_RESPONSE_SCHEMA,
    FINAL_RESPONSE_SCHEMA
)
import json
import os

class LLMService:
    def __init__(self, model="gpt-4o-mini"):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set. Please set it before running.")
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.default_max_output_tokens = 2048
        self.max_output_ceiling = 8192
        self.max_retries = 3

    def _extract_json(self, response):
        """
        Structured Outputs via responses.create return JSON as text.
        This is guaranteed to be valid JSON matching the schema.
        """
        if response.status != "completed":
            raise RuntimeError(f"LLM call failed: {response}")

        return json.loads(response.output_text)

    def _call_with_schema(self, prompt: str, schema_name: str, schema: dict, temperature: float = 1.0):
        max_tokens = self.default_max_output_tokens
        attempt = 0

        while attempt < self.max_retries:
            response = self.client.responses.create(
                model=self.model,
                input=prompt,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": schema_name,
                        "schema": schema,
                        "strict": True
                    }
                },
                temperature=temperature,
                max_output_tokens=max_tokens,
            )

            if response.status == "completed":
                return self._extract_json(response)

            details = getattr(response, "incomplete_details", None)
            hit_limit = (
                response.status == "incomplete"
                and details is not None
                and getattr(details, "reason", None) == "max_output_tokens"
            )

            if hit_limit and max_tokens < self.max_output_ceiling:
                attempt += 1
                previous_cap = max_tokens
                max_tokens = min(max_tokens * 2, self.max_output_ceiling)
                print(f"LLM output hit {previous_cap} tokens; retrying with cap {max_tokens}.")
                continue

            raise RuntimeError(f"LLM call failed: {response}")

        raise RuntimeError("LLM call failed after retrying due to max token limit.")

    def generate_internal_node(self, prompt: str) -> dict:
        return self._call_with_schema(
            prompt,
            schema_name="node_response",
            schema=NODE_RESPONSE_SCHEMA,
            temperature=1,
        )

    def generate_leaf_answer(self, prompt: str) -> dict:
        return self._call_with_schema(
            prompt,
            schema_name="answer_response",
            schema=ANSWER_RESPONSE_SCHEMA,
            temperature=1,
        )

    def generate_final_answer(self, prompt: str) -> dict:
        return self._call_with_schema(
            prompt,
            schema_name="final_response",
            schema=FINAL_RESPONSE_SCHEMA,
            temperature=1,
        )
