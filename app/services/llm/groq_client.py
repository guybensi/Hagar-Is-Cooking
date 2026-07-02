import json

from groq import (
    APIConnectionError,
    APITimeoutError,
    AsyncGroq,
    InternalServerError,
    RateLimitError,
)
from pydantic import BaseModel, ValidationError

from app.prompts import normalize_query
from app.services.llm.schema_builder import build_json_schema_response_format
from app.utils.logging import get_logger
from app.utils.retry import retry_transient_errors

logger = get_logger(__name__)

_TRANSIENT_GROQ_ERRORS = (APIConnectionError, APITimeoutError, RateLimitError, InternalServerError)


class LLMStructuringError(Exception):
    """Raised when Groq fails to produce a schema-valid structured response."""


class _NormalizedQuery(BaseModel):
    search_query: str


class GroqClient:
    """Thin async wrapper around the Groq SDK providing structured-JSON completions."""

    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncGroq(api_key=api_key)
        self._model = model

    @retry_transient_errors(*_TRANSIENT_GROQ_ERRORS)
    async def _create_completion(
        self, *, system_prompt: str, user_prompt: str, response_format: dict
    ):
        return await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=response_format,
        )

    async def _structured_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
        max_validation_retries: int = 2,
    ) -> BaseModel:
        response_format = build_json_schema_response_format(response_model)
        prompt = user_prompt
        last_error: Exception | None = None

        for attempt in range(max_validation_retries + 1):
            completion = await self._create_completion(
                system_prompt=system_prompt, user_prompt=prompt, response_format=response_format
            )
            raw_content = completion.choices[0].message.content

            try:
                return response_model.model_validate_json(raw_content)
            except (ValidationError, json.JSONDecodeError) as exc:
                last_error = exc
                logger.warning(
                    "structured_completion_validation_failed",
                    model=response_model.__name__,
                    attempt=attempt,
                    error=str(exc),
                )
                prompt = (
                    f"{user_prompt}\n\n"
                    f"Your previous response was invalid: {exc}\n"
                    "Return ONLY valid JSON matching the required schema."
                )

        raise LLMStructuringError(
            f"Groq failed to produce a valid {response_model.__name__} after "
            f"{max_validation_retries + 1} attempts: {last_error}"
        )

    async def normalize_dish_query(self, user_text: str) -> str:
        result = await self._structured_completion(
            system_prompt=normalize_query.SYSTEM_PROMPT,
            user_prompt=normalize_query.build_user_prompt(user_text),
            response_model=_NormalizedQuery,
        )
        return result.search_query
