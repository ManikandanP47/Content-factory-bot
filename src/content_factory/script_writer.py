from __future__ import annotations

import json
import re
from typing import Any

import httpx

from content_factory.models import Beat, VideoScript


SYSTEM_PROMPT = """You are an elite short-form content creator, influencer, and script writer.
Write a vertical Shorts/Reels script (~45 seconds spoken) for the niche given.
Return ONLY valid JSON with this exact shape:
{
  "title": "under 70 chars, punchy, include #Shorts at end or we add it",
  "hook": "first 1-2 spoken sentences that stop the scroll",
  "beats": [
    {"text": "spoken line", "on_screen": "short caption <= 8 words", "motion": "fade|punch|slide"}
  ],
  "cta": "closing spoken call to action",
  "description": "YouTube/IG description 1-3 sentences",
  "hashtags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "narration": "full spoken script as one continuous paragraph (hook + beats + cta)"
}
Rules:
- 3 to 5 beats
- Direct, punchy, peer-to-peer tone
- No fluff openings like 'Hey guys'
- No markdown, no code fences, JSON only
"""


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise
        return json.loads(match.group(0))


def _fallback_script(topic: str, niche: str, tone: str) -> VideoScript:
    title = topic.strip().rstrip(".")
    if len(title) > 60:
        title = title[:57] + "..."
    hook = f"Most people get {topic.lower()} completely wrong."
    beats = [
        Beat(
            text=f"Here's the truth about {topic}: clarity beats hustle.",
            on_screen="Clarity beats hustle",
            motion="punch",
        ),
        Beat(
            text="Pick one system. Protect two deep-work blocks. Kill everything else.",
            on_screen="One system. Two blocks.",
            motion="fade",
        ),
        Beat(
            text="Track one metric for seven days before you add another tool.",
            on_screen="One metric. Seven days.",
            motion="slide",
        ),
        Beat(
            text=f"That's how operators actually win at {topic.lower()}.",
            on_screen="Operators win quietly",
            motion="fade",
        ),
    ]
    cta = "Save this. Try it tomorrow. Follow for the next move."
    narration = " ".join(
        [hook] + [b.text for b in beats] + [cta]
    )
    return VideoScript(
        topic=topic,
        title=f"{title} #Shorts",
        hook=hook,
        beats=beats,
        cta=cta,
        description=(
            f"{topic} — a {niche} short. {tone.capitalize()}. "
            "Follow for practical playbooks."
        ),
        hashtags=["productivity", "foundertips", "shorts", "habits", "focus"],
        narration=narration,
    )


def write_script(topic: str, config: dict[str, Any]) -> VideoScript:
    niche = config.get("niche", "productivity")
    tone = config.get("tone", "direct")
    ollama = config.get("ollama", {})
    base_url = ollama.get("base_url", "http://127.0.0.1:11434").rstrip("/")
    model = ollama.get("model", "llama3.2")
    timeout = float(ollama.get("timeout_seconds", 120))

    user = (
        f"Niche: {niche}\nTone: {tone}\nTopic: {topic}\n"
        "Write the JSON script now."
    )

    try:
        with httpx.Client(timeout=timeout) as client:
            # check server
            client.get(f"{base_url}/api/tags")
            resp = client.post(
                f"{base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": user,
                    "system": SYSTEM_PROMPT,
                    "stream": False,
                    "format": "json",
                },
            )
            resp.raise_for_status()
            raw = resp.json().get("response", "")
            data = _extract_json(raw)
            beats = [Beat(**b) for b in data.get("beats", [])]
            if not beats:
                raise ValueError("LLM returned no beats")
            title = data.get("title") or topic
            if "#Shorts" not in title and "#shorts" not in title:
                title = f"{title} #Shorts"
            script = VideoScript(
                topic=topic,
                title=title,
                hook=data["hook"],
                beats=beats,
                cta=data.get("cta") or "Follow for more.",
                description=data.get("description") or topic,
                hashtags=list(data.get("hashtags") or []),
                narration=data.get("narration") or "",
            )
            if not script.narration:
                script.narration = script.full_narration()
            return script
    except Exception:
        return _fallback_script(topic, niche, tone)
