import json
import logging
import re

from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from backend.services.ai_settings_service import get_active_ai_settings

from .manual_views import DraftSerializer, SystemAdminOnly
from .templates_service import LAYOUT_DEFAULTS, PLACEHOLDERS


logger = logging.getLogger(__name__)
LAYOUT_STYLES = (
    "Royal Navy & Gold", "Emerald Prestige", "Minimalist Editorial", "Crimson Celebration",
    "Modern Sapphire Blue", "Botanical Pastel", "Midnight Starlight",
    "Sunrise Amber & Terracotta", "Classic Diplomatic", "Festive Confetti",
)


class BirthdayDraftThrottle(UserRateThrottle):
    scope = "birthday-draft"
    rate = "10/min"


def complete_draft(prompt: str) -> str:
    config = get_active_ai_settings()
    model = config.get("llm_model", "gpt-6-luna")
    if config.get("openai_api_key"):
        from llama_index.llms.openai import OpenAI

        actual_model = "gpt-4o-mini" if model == "gpt-6-luna" else model
        llm = OpenAI(model=actual_model, api_key=config["openai_api_key"], timeout=15, max_retries=0)
    else:
        raise RuntimeError("Birthday draft provider unavailable")
    return llm.complete(prompt).text


@api_view(["POST"])
@permission_classes([SystemAdminOnly])
@throttle_classes([BirthdayDraftThrottle])
def draft_api(request):
    instruction = request.data.get("instruction") if isinstance(request.data, dict) else None
    if not isinstance(instruction, str) or not 1 <= len(instruction.strip()) <= 1500:
        return Response({"error": "invalidInstruction"}, status=400)

    layouts = ", ".join(f"{key}: {name}" for key, name in zip(LAYOUT_DEFAULTS, LAYOUT_STYLES))
    variables = ", ".join("{{ " + name + " }}" for name in PLACEHOLDERS)
    prompt = (
        "Draft a reusable, professional corporate birthday email in the language of the instruction. "
        "Return one JSON object with three string keys: layout (two-digit ID), subject (one line), message "
        "(plain text, no markup, use blank lines between paragraphs). "
        "Use placeholders for personal details and never invent personal information or reveal age or birth year. "
        f"Allowed layouts: {layouts}. Allowed placeholders: {variables}. "
        f"Administrator instruction: {json.dumps(instruction.strip(), ensure_ascii=False)}"
    )
    try:
        raw = complete_draft(prompt).strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL)
        serializer = DraftSerializer(data=json.loads(fenced[1] if fenced else raw))
        if serializer.is_valid():
            return Response({"draft": serializer.validated_data})
    except Exception as error:
        logger.warning("Birthday draft unavailable (%s)", type(error).__name__)
    return Response({"error": "aiUnavailable"}, status=503)
