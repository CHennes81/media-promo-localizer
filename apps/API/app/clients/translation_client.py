"""
Translation client implementations using LLM APIs.
"""
import json
import logging
import time
from typing import List, Optional

from openai import AsyncOpenAI

from app.clients.interfaces import ITranslationClient, TranslatedRegion
from app.models.jobs import DetectedText

logger = logging.getLogger("media_promo_localizer")


class LlmTranslationClient(ITranslationClient):
    """OpenAI-based translation client."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        Initialize OpenAI translation client.

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o-mini)
        """
        self.api_key = api_key
        self.model = model
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for live translation mode")

    async def translate_text_regions(
        self,
        regions: List[DetectedText],
        target_locale: str,
        job_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> List[TranslatedRegion]:
        """
        Translate text regions to target locale using OpenAI.

        Args:
            regions: List of detected text regions to translate
            target_locale: Target locale code (BCP-47, e.g., "fr-FR")
            job_id: Optional job ID for logging context

        Returns:
            List of TranslatedRegion objects with translated text

        Raises:
            Exception: If translation fails
        """
        # Log before call
        endpoint_base = "https://api.openai.com/v1/chat/completions"
        outbound_timestamp = time.time()

        # Initialize correlation string and content before try block
        correlation = []
        if request_id:
            correlation.append(f"request={request_id}")
        if job_id:
            correlation.append(f"job={job_id}")
        correlation_str = " ".join(correlation) if correlation else ""

        # Initialize content to empty string (will be set after API call)
        content = ""

        if job_id or request_id:
            logger.info(
                f"ServiceCall {correlation_str} service=TRANSLATION endpoint={endpoint_base} "
                f"outbound_timestamp={outbound_timestamp:.3f} model={self.model}"
            )

        try:
            client = AsyncOpenAI(api_key=self.api_key)

            # Build prompt for translation
            # Group regions by role for better context
            regions_by_role = {}
            for region in regions:
                if region.role not in regions_by_role:
                    regions_by_role[region.role] = []
                regions_by_role[region.role].append(region)

            # Build translation request
            regions_data = [
                {
                    "text": region.text,
                    "role": region.role,
                    "boundingBox": region.boundingBox,
                }
                for region in regions
            ]

            prompt = self._build_translation_prompt(regions_data, target_locale)

            # Call OpenAI API
            call_start = time.perf_counter()
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional translator specializing in marketing and promotional materials for film and TV. Translate text while preserving tone, style, and cultural context.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            call_duration_ms = int((time.perf_counter() - call_start) * 1000)
            response_timestamp = time.time()

            # Parse response
            content = response.choices[0].message.content if response.choices and response.choices[0].message else ""

            # Log response (OpenAI doesn't return HTTP status in the same way, but we can log success)
            status_code = 200  # OpenAI client handles errors via exceptions
            # Calculate response size
            response_size = len(content.encode('utf-8')) if content else 0

            logger.info(
                f"ServiceResponse {correlation_str} service=TRANSLATION status={status_code} "
                f"response_timestamp={response_timestamp:.3f} durationMs={call_duration_ms} "
                f"responseSizeBytes={response_size}"
            )
            if not content:
                raise Exception("Empty response from translation API")

            translation_result = json.loads(content)

            # Map translations back to regions
            translated_regions: List[TranslatedRegion] = []
            translations = translation_result.get("translations", [])

            # Create a map of original text to translation
            translation_map = {
                item.get("originalText", ""): item.get("translatedText", "")
                for item in translations
            }

            for region in regions:
                translated_text = translation_map.get(region.text, region.text)
                translated_regions.append(
                    TranslatedRegion(
                        original_text=region.text,
                        translated_text=translated_text,
                        bounding_box=region.boundingBox,
                        role=region.role,
                    )
                )

            logger.info(
                f"Translated {len(translated_regions)} regions to {target_locale}"
            )
            return translated_regions

        except json.JSONDecodeError as e:
            response_timestamp = time.time()
            # correlation_str and content are guaranteed to be defined before try block
            logger.error(
                f"ServiceResponse {correlation_str} service=TRANSLATION status=500 "
                f"response_timestamp={response_timestamp:.3f} error=JSONDecodeError",
                exc_info=True,
            )
            raise Exception("Invalid response format from translation API")
        except Exception as e:
            response_timestamp = time.time()
            # correlation_str is guaranteed to be defined before try block
            error_name = type(e).__name__ if e else "UnknownError"
            error_message = str(e) if e else "Unknown error"
            logger.error(
                f"ServiceResponse {correlation_str} service=TRANSLATION status=500 "
                f"response_timestamp={response_timestamp:.3f} error={error_name}",
                exc_info=True,
            )
            raise Exception(f"Translation processing failed: {error_message}")

    def _build_translation_prompt(
        self, regions_data: List[dict], target_locale: str
    ) -> str:
        """
        Build a prompt for translation.

        Args:
            regions_data: List of region data dicts
            target_locale: Target locale code

        Returns:
            Prompt string
        """
        # Extract locale name for better context
        locale_map = {
            "fr-FR": "French (France)",
            "es-MX": "Spanish (Mexico)",
            "pt-BR": "Portuguese (Brazil)",
            "ja-JP": "Japanese (Japan)",
            "de-DE": "German (Germany)",
            "ko-KR": "Korean (South Korea)",
            "ru-RU": "Russian (Russia)",
            "vi-VN": "Vietnamese (Vietnam)",
        }
        locale_name = locale_map.get(target_locale, target_locale)

        prompt = f"""Translate the following text regions from a promotional poster to {locale_name} ({target_locale}).

Rules:
- Preserve the tone and style appropriate for marketing materials
- For titles: keep them impactful and cinematic
- For taglines: adapt creatively (transcreation) rather than literal translation
- For credits (director, producer, cast names): keep names in original form, translate only role labels
- For URLs, social handles, and rating badges: do NOT translate, return the original text
- For release messages: adapt to local date/time formats and cultural context

Return a JSON object with this structure:
{{
  "translations": [
    {{
      "originalText": "original text here",
      "translatedText": "translated text here"
    }}
  ]
}}

Text regions to translate:
{json.dumps(regions_data, indent=2, ensure_ascii=False)}
"""

        return prompt
