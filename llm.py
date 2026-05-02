import json
import anthropic
from prompts import build_system_prompt, build_user_prompt


def extract_action_items(transcript: str, roster: dict) -> list[dict]:
    client = anthropic.Anthropic()

    system_prompt = build_system_prompt(roster)
    user_prompt = build_user_prompt(transcript)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)
