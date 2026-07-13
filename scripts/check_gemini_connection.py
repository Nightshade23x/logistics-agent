from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.smart_answer import generate_smart_answer, get_gemini_api_key, get_gemini_model


def main() -> None:
    key = get_gemini_api_key()
    model = get_gemini_model()

    print("=== Gemini Connection Check ===")
    print("Gemini key loaded:", bool(key))
    print("Gemini key length:", len(key))
    print("Gemini key starts with:", key[:6] + "..." if key else "NONE")
    print("Gemini model:", model)
    print()

    if not key:
        raise SystemExit("No Gemini key loaded. Check config/local_secrets.env")

    result = generate_smart_answer(
        question="Say Gemini is working in one short sentence.",
        payload={
            "decision": "needs_more_information",
            "detected_intent": "shopping",
            "agents_called": ["shopping_agent"],
        },
        fallback_answer="Fallback answer only.",
    )

    print("mode:", result["mode"])
    print("provider:", result["provider"])
    print("model:", result["model"])
    print("status:", result["status"])
    print("answer:", result["answer"][:500])

    if result.get("retry_after_seconds"):
        print("retry_after_seconds:", result["retry_after_seconds"])

    if result.get("error"):
        print()
        print("ERROR:")
        print(result["error"])

    if result["mode"] == "gemini":
        print()
        print("RESULT: PASS - Gemini is working.")
    else:
        print()
        print("RESULT: FALLBACK - Gemini was reached but did not generate.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
