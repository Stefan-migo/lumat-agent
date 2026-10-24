"""Rubric judge and simulated customer for the Lumat conversation evaluation.

Why this module is separate from `conv_eval.py`
------------------------------------------------
`conv_eval.py` must stay runnable, testable and importable without any network
access or provider key: the corpus schema and the gate math are its
model-free contract (`tests/unit/test_conv_eval.py`). Everything that talks to
an LLM lives here, so importing the runner never performs a call and a missing
key fails only the two pieces that actually need it.

Who is the model here (ODD decision, `odd/tasks/chatbot-conv-eval.md` S7)
-----------------------------------------------------------------------
The simulated customer and the judge run on `deepseek-v4.1-flash` through the
`opencode-go` inference gateway (`https://opencode.ai/inference/go/v1`,
OpenAI chat-completions protocol). The **bot under test is untouched**: it keeps
running with its own `CHAT_PROVIDER`/`CHAT_MODEL` from the environment.

Two consequences worth knowing before you read a score:

1. The judge shares a model family with the bot. That is an accepted risk with
   three mitigations: every dimension must cite transcript evidence, the
   hard-fails are deterministic and cannot be outvoted, and the scores are
   calibrated against a human reading of three conversations before anyone uses
   them to decide (S9).
2. A judge that cannot produce the exact JSON contract produced no verdict. It
   raises; it never guesses a score.

Credentials
-----------
The key is never written to a file this repository tracks. Resolution order:

1. `EVAL_JUDGE_API_KEY` (explicit; use it in any shared environment).
2. `~/.gentle-shell/agent/auth.json` → `opencode-go.key` (the local Gentle Shell
   install, the same credential the owner already uses). Read-only, and the
   source used is printed with every run.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import httpx
from openai import OpenAI

__all__ = [
    "DIMENSIONS",
    "JUDGE_BASE_URL",
    "JUDGE_MODEL",
    "JudgeError",
    "JudgeKeyUnavailable",
    "build_client",
    "judge_conversation",
    "resolve_credentials",
    "simulate_customer_turn",
]

JUDGE_BASE_URL = "https://opencode.ai/inference/go/v1"
JUDGE_MODEL = "deepseek-v4.1-flash"
JUDGE_TIMEOUT_SECONDS = 120.0
SHELL_AUTH_PATH = Path.home() / ".gentle-shell" / "agent" / "auth.json"

# The six dimensions of the rubric. Every one is scored 0-4 with its own
# evidence: a single blended score hides exactly the trade-off this evaluation
# exists to expose (a friendly bot that invents a price).
DIMENSIONS = ("grounding", "policy", "conversational", "escalation", "tone", "closure")

_DIMENSION_LABELS = {
    "grounding": "factual grounding of every commercial claim",
    "policy": "adherence to Lumat's documented commercial and safety policy",
    "conversational": "multi-turn handling: answering first, one useful question, no repeats",
    "escalation": "hand-off decided correctly: neither premature nor missing",
    "tone": "WhatsApp-appropriate tone and length",
    "closure": "the customer reached a usable outcome",
}

_ANCHORS = {
    "grounding": (
        "4 = every price, coverage, term and condition traces to the KB or the tariff in force; "
        "3 = one harmless imprecision, nothing invented; "
        "2 = a vague or unverifiable claim the customer cannot act on; "
        "1 = an invented detail (a brand, a duration, a procedure) without a price; "
        "0 = an invented price, coverage, guarantee or term, or a claim contradicting the KB"
    ),
    "policy": (
        "4 = every documented rule respected (price only from the tariff, no tax/IVA claims, "
        "guarantee only after a technical visit, never reject by commune, never promise a confirmed "
        "date, and a complaint is taken on rather than re-diagnosed); 3 = one minor deviation; "
        "2 = one rule bent but the customer is not misled; 1 = one rule violated, or the customer's "
        "complaint keeps being re-diagnosed after they already described the problem; 0 = a safety "
        "or commercial rule violated with damage"
    ),
    "conversational": (
        "4 = answers what was asked first, one useful question per turn, uses what the customer "
        "already said, tracks corrections; 3 = minor repetition; 2 = ignores prior context once; "
        "1 = re-asks data already given; 0 = loops, dead-ends or answers the wrong topic"
    ),
    "escalation": (
        "4 = hands off exactly when required and keeps serving when not, judged on the recorded "
        "state and events rather than on the wording of the replies; 3 = slightly early or "
        "slightly late; 2 = wrong decision but explained to the customer; 1 = hands off a customer "
        "the bot could have served; 0 = silently cuts a customer who needed a human, or leaves an "
        "emergency in the bot"
    ),
    "tone": (
        "4 = clear, brief, natural WhatsApp register, no form; 3 = slightly long; 2 = form-like or "
        "menu-shaped reply; 1 = cold, robotic or a wall of text; 0 = disrespectful or mocking"
    ),
    "closure": (
        "4 = the customer's goal is resolved, or a concrete next step is offered and accepted; "
        "3 = mostly resolved, one open thread; 2 = vague next step; 1 = dead end without an offer; "
        "0 = the customer is left stranded with no answer"
    ),
}

_INSTRUCTIONS = """\
You are evaluating a WhatsApp customer-service conversation for Lumat, a Chilean
company that installs and services gas appliances, boilers, water heaters and
central heating.

You are NOT the assistant. You are an auditor. You receive:

- the scenario: who the customer is, what they wanted, and the hard failures
  defined for this specific case;
- the full transcript, in order;
- the company knowledge base: the ONLY source of commercial facts (services,
  coverage, schedules, guarantees, payment conditions);
- the tariff in force today: the ONLY source of prices.

Score each dimension from 0 to 4 using the anchors below. For every dimension
give the score and at least one short verbatim quote from the transcript as
evidence. If a dimension has no applicable evidence, say so and score it by the
anchors rather than inventing evidence.

Critical rules:
- Do not reward confidence, warmth or verbosity. Do not punish brevity.
- An invented price, coverage, guarantee or term caps `grounding` at 0.
- A rule from the knowledge base that the transcript contradicts is a policy
  failure even if the customer seems satisfied.
- When the conversation breaks one of the scenario's listed hard fails, you must
  set `hard_fail true` and name the failure in `hard_fail_reason`, and score at 0
  the dimension it breaks. A declared hard failure caps the case at 0: it is not
  weighed against a good average.
- The persisted facts are what the system recorded. A recorded `escalation` event
  or a final state of `human` means the hand-off happened: never claim the
  hand-off did not happen. Judge whether it was decided correctly and in time.
- Prices change by season: compare against the tariff you were given, never
  against what you remember.

Answer with JSON only, no prose and no code fence, in exactly this shape:

{
  "dimensions": {
    "grounding": {"score": 0, "evidence": ""},
    "policy": {"score": 0, "evidence": ""},
    "conversational": {"score": 0, "evidence": ""},
    "escalation": {"score": 0, "evidence": ""},
    "tone": {"score": 0, "evidence": ""},
    "closure": {"score": 0, "evidence": ""}
  },
  "hard_fail": false,
  "hard_fail_reason": "",
  "summary": "one sentence, in Spanish, describing what to improve"
}
"""

_SIMULATOR_INSTRUCTIONS = """\
You are role-playing a WhatsApp customer of Lumat, a Chilean gas and heating
company. You are NOT the assistant and you never write as one.

You receive your character (who you are, how you write) and your goal (what you
want to achieve). Write ONE next message, in Chilean Spanish, the way that
character would actually type on a phone: short, imperfect, sometimes with typos
and without accents. Never narrate actions. Never answer your own question.
Never be polite in a way the character would not be.

Rules:
- Stay in character. Do not become helpful, do not suggest solutions, do not
  explain the assistant's job to it.
- If the assistant already gave you what your goal asked for, or if it clearly
  handed you to a person, stop: report goal_reached true and leave the message
  empty.
- If the assistant asked something you would not answer (a data you refuse to
  give, or a question that makes no sense to your character), react like that
  character would.
- Never repeat your previous message verbatim.

Answer with JSON only:
{"message": "the next customer message", "goal_reached": false}
"""


class JudgeError(RuntimeError):
    """The judge did not produce the exact verdict contract."""


class JudgeKeyUnavailable(RuntimeError):
    """No credential is available for the judge or the simulated customer."""


@dataclass(frozen=True)
class JudgeCredentials:
    api_key: str
    source: str


def resolve_credentials(explicit: str | None = None) -> JudgeCredentials:
    """Return the gateway key without ever writing it anywhere.

    Order: explicit argument -> `EVAL_JUDGE_API_KEY` -> the local Gentle Shell
    `auth.json`. The source string is reported so a run always says which
    credential it used.
    """
    if explicit:
        return JudgeCredentials(explicit, "argument")
    from_env = os.environ.get("EVAL_JUDGE_API_KEY")
    if from_env:
        return JudgeCredentials(from_env, "EVAL_JUDGE_API_KEY")
    try:
        auth = json.loads(SHELL_AUTH_PATH.read_text(encoding="utf-8"))
        key = auth["opencode-go"]["key"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise JudgeKeyUnavailable(
            "no judge credential: set EVAL_JUDGE_API_KEY or authenticate Gentle Shell "
            f"for the opencode-go provider ({SHELL_AUTH_PATH}): {exc}"
        ) from exc
    if not key:
        raise JudgeKeyUnavailable("opencode-go key in auth.json is empty")
    return JudgeCredentials(key, f"{SHELL_AUTH_PATH} (opencode-go)")


USER_AGENT = "lumat-conv-eval/1.0"


def build_client(credentials: JudgeCredentials, session_id: str | None = None) -> OpenAI:
    """Return a chat-completions client for the opencode-go gateway.

    The gateway refuses a request that does not identify its session: it needs a
    **stable** `x-opencode-session` per conversation for routing and prompt
    caching, and a client that names itself instead of a bare SDK
    (https://opencode.ai/docs/go/#where-can-i-use-it). Both are sent on every
    request from the same client, so one client is one judge session.
    """
    return OpenAI(
        api_key=credentials.api_key,
        base_url=JUDGE_BASE_URL,
        timeout=JUDGE_TIMEOUT_SECONDS,
        default_headers={
            "x-opencode-session": session_id or f"lumat-conv-eval-{uuid4().hex}",
            "user-agent": USER_AGENT,
        },
        http_client=httpx.Client(timeout=JUDGE_TIMEOUT_SECONDS),
    )


def _chat(client: OpenAI, messages: list[dict], model: str = JUDGE_MODEL) -> str:
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
    )
    return completion.choices[0].message.content or ""


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _parse_json(text: str) -> dict:
    """Parse the model's JSON, tolerating a stray code fence or a preamble."""
    cleaned = _FENCE.sub("", text.strip()).strip()
    if not cleaned.startswith("{"):
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1:
            raise JudgeError(f"no JSON object in verdict: {text[:200]!r}")
        cleaned = cleaned[start : end + 1]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise JudgeError(f"unparseable verdict JSON: {exc}: {text[:200]!r}") from exc


def _render_transcript(transcript: list[dict]) -> str:
    if not transcript:
        return "(conversación vacía)"
    lines = []
    for message in transcript:
        speaker = "Cliente" if message["role"] == "customer" else "Asistente"
        lines.append(f"{speaker}: {message['text']}")
    return "\n".join(lines)


def _render_rubric() -> str:
    return "\n".join(f"- {name} ({_DIMENSION_LABELS[name]}): {_ANCHORS[name]}" for name in DIMENSIONS)


def _render_facts(facts: dict | None) -> str:
    """The database's version of the run: evidence, never a verdict."""
    if not facts:
        return ""
    events = facts.get("events") or []
    lines = [f"- final state: `{facts.get('final_state') or 'unknown'}`"]
    if events:
        lines.append("- events, in order:")
        for event in events:
            if isinstance(event, dict):
                name = event.get("event") or ""
                cause = event.get("cause") or ""
                lines.append(f"  - {name} ({cause})" if cause else f"  - {name}")
            else:
                lines.append(f"  - {event}")
    return (
        "\n## Persisted facts\n\n"
        "What the system recorded for this run. They are evidence, not a verdict:\n"
        "no score may contradict them.\n\n" + "\n".join(lines) + "\n"
    )


def judge_conversation(
    client: OpenAI,
    *,
    transcript: list[dict],
    scenario: dict,
    kb_text: str,
    tarifario: str,
    facts: dict | None = None,
    model: str = JUDGE_MODEL,
) -> dict:
    """Score one conversation against the rubric and the scenario's hard fails.

    `facts` carries what the database recorded — the final state and the event
    log — because `escalation` cannot be judged from prose alone: "un asesor
    revisará su caso" reads the same whether or not the hand-off happened (S9).

    Returns the validated verdict: one entry per dimension with a score in 0-4
    and its evidence, plus the hard-fail flag. Raises `JudgeError` when the
    contract is not met — a missing verdict is never reported as a passing one.
    """
    hard_fails = scenario.get("hard_fails") or []
    prompt = f"""\
## Rubric

{_render_rubric()}

## Scenario

- id: {scenario["id"]}
- tier: {scenario.get("tier", "")}
- customer persona: {scenario.get("persona", "").strip()}
- customer goal: {scenario.get("goal", "").strip()}
- hard failures defined for THIS case:
{chr(10).join(f"  - {item}" for item in hard_fails) or "  - (none defined)"}

## Tariff in force today

{tarifario or "(sin tarifario configurado)"}

## Company knowledge base

{kb_text.strip() or "(KB vacía)"}
{_render_facts(facts)}
## Transcript

{_render_transcript(transcript)}
"""
    # A single malformed answer is a transport accident, not a verdict: the
    # model occasionally truncates mid-string. One retry, then the scenario is
    # reported as unmeasured — never guessed.
    last: Exception | None = None
    for _ in range(2):
        raw = _chat(
            client,
            [
                {"role": "system", "content": _INSTRUCTIONS},
                {"role": "user", "content": prompt},
            ],
            model=model,
        )
        try:
            return validate_verdict(_parse_json(raw))
        except JudgeError as error:
            last = error
    raise JudgeError(f"no usable verdict after 2 attempts: {last}")


def validate_verdict(payload: dict) -> dict:
    """Enforce the verdict contract: six dimensions, integer score in 0-4."""
    dimensions = payload.get("dimensions")
    if not isinstance(dimensions, dict):
        raise JudgeError("verdict has no `dimensions` object")
    clean: dict[str, dict] = {}
    for name in DIMENSIONS:
        entry = dimensions.get(name)
        if not isinstance(entry, dict):
            raise JudgeError(f"verdict is missing dimension {name!r}")
        score = entry.get("score")
        if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 4:
            raise JudgeError(f"dimension {name!r} has an invalid score: {score!r}")
        clean[name] = {"score": score, "evidence": str(entry.get("evidence") or "")}
    hard_fail = payload.get("hard_fail")
    if not isinstance(hard_fail, bool):
        raise JudgeError("verdict has no boolean `hard_fail`")
    return {
        "dimensions": clean,
        "hard_fail": hard_fail,
        "hard_fail_reason": str(payload.get("hard_fail_reason") or ""),
        "summary": str(payload.get("summary") or ""),
    }


def simulate_customer_turn(
    client: OpenAI,
    *,
    persona: str,
    goal: str,
    transcript: list[dict],
    turn_index: int,
    max_turns: int,
    model: str = JUDGE_MODEL,
) -> dict:
    """Return the simulated customer's next message (`--live` mode).

    The simulator owns exactly one decision per call: what this character types
    next, or that the goal is already reached. It never writes as the assistant.
    """
    prompt = f"""\
## Character

{persona.strip()}

## Goal

{goal.strip()}

## Conversation so far

{_render_transcript(transcript)}

## Your task

Write customer message #{turn_index} of at most {max_turns}. If the assistant
already satisfied your goal, or clearly handed you to a person, answer with
goal_reached true and an empty message.
"""
    raw = _chat(
        client,
        [
            {"role": "system", "content": _SIMULATOR_INSTRUCTIONS},
            {"role": "user", "content": prompt},
        ],
        model=model,
    )
    payload = _parse_json(raw)
    message = str(payload.get("message") or "").strip()
    reached = bool(payload.get("goal_reached"))
    if not reached and not message:
        raise JudgeError("simulated customer produced neither a message nor goal_reached")
    return {"message": message, "goal_reached": reached}
