import json
import re
import time
import config
from google import genai
from google.genai import types

client = genai.Client(api_key=getattr(config, "GEMINI_API_KEY", None))

MODEL_CANDIDATES = ['gemini-3.6-flash', 'gemini-3.5-flash-lite']

# Exact wording required whenever the query isn't about planning a Mumbai visit.
OFF_TOPIC_MESSAGE = "I can only help you plan your Mumbai trip"

# Local safety net: even if the model marks is_travel_related=True, scan the
# text it actually generated for signs that a math/trivia/code question snuck
# in anyway (e.g. a query disguised as a travel request). Pure regex, no
# extra API call, so it adds no latency for genuine users.
_LEAK_PATTERNS = [
    r"```",                                   # code fences
    r"\bdef\s+\w+\s*\(",                       # python function defs
    r"\bfunction\s*\(",                        # js function defs
    r"<\s*(html|script|div)[\s>]",             # markup/code snippets
    r"\bimport\s+\w+",                         # import statements
    r"\bthe answer is\b",                      # direct Q&A phrasing
    r"\bequals?\b\s*\d",                       # "equals 42" style math answers
    r"\d+\s*[\+\-\*/x×]\s*\d+\s*=",             # arithmetic expressions like 15+23=
    r"\bpresident of\b|\bprime minister of\b",  # general political trivia
    r"\bcapital of\b",                          # general geography trivia
]
_LEAK_RE = re.compile("|".join(_LEAK_PATTERNS), re.IGNORECASE)


def _collect_text_fields(payload):
    """Pull out every free-text string the model generated, so we can scan it."""
    texts = []
    for item in payload.get("itinerary", []) or []:
        texts.append(str(item.get("action", "")))
        texts.append(str(item.get("description", "")))
    texts.extend(str(f) for f in (payload.get("food_suggestions", []) or []))
    for v in (payload.get("budget_breakdown", {}) or {}).values():
        texts.append(str(v))
    return texts


def _has_offtopic_leak(payload):
    return any(_LEAK_RE.search(text) for text in _collect_text_fields(payload))


def _decline_response():
    return {
        "is_travel_related": False,
        "decline_message": OFF_TOPIC_MESSAGE,
        "recommended_place_ids": [],
        "itinerary": [],
        "food_suggestions": [],
        "budget_breakdown": {},
    }


# ---------------------------------------------------------------------
# BODA identity / creator responses
# ---------------------------------------------------------------------
# These are exact, fixed answers. The model is never consulted for them,
# so the wording can never drift and no API call is spent on them.

BODA_INTRO_MESSAGE = (
    "I'm BODA—stand for \"Bombay, Once Discovered, Always.\" Think of me as a "
    "local friend who knows Mumbai inside out. Skip the usual tourist "
    "spots—just tell me where you are, your budget, or how much time you've "
    "got, and I'll give you real, hidden spots to explore."
)

DEVELOPER_MESSAGE = (
    "I was developed by Rohit Gaikwad and Harsh Lodat. Both are B.Sc. "
    "Computer Science students at Patkar-Varde College who built me to help "
    "people explore the real, unfiltered Mumbai. Where in the city are you "
    "starting from today?"
)

BOTH_CREATORS_MESSAGE = (
    "Rohit Gaikwad and Harsh Lodat are Computer Science students at "
    "Patkar-Varde College (B.Sc. CS) and the creators behind BODA! What "
    "part of Mumbai are you looking to explore today?"
)

ROHIT_ONLY_MESSAGE = (
    "Rohit Gaikwad is a Computer Science student at Patkar-Varde College "
    "(B.Sc. CS) and one of the creators behind BODA! What part of Mumbai "
    "are you looking to explore today?"
)

HARSH_ONLY_MESSAGE = (
    "Harsh Lodat is a Computer Science student at Patkar-Varde College "
    "(B.Sc. CS) and one of the creators behind BODA! What part of Mumbai "
    "are you looking to explore today?"
)

# First match wins — checked in this order.
_ABOUT_BODA_RE = re.compile(
    r"\b(what('?s| is) boda|who is boda|about boda|tell me about boda)\b",
    re.IGNORECASE,
)
_DEVELOPER_RE = re.compile(
    r"\b(developer|father|creator|who (made|built|created|developed) you|"
    r"who is your (developer|creator|father))\b",
    re.IGNORECASE,
)
_ROHIT_RE = re.compile(r"\brohit(\s+gaikwad)?\b", re.IGNORECASE)
_HARSH_RE = re.compile(r"\bharsh(\s+lodat)?\b", re.IGNORECASE)


def check_scripted_response(user_query):
    """
    Returns a fixed BODA identity/creator response dict if the query
    matches one of the reserved questions, else None — meaning the caller
    should fall through to the normal Gemini itinerary flow.
    """
    text = user_query or ""

    if _ABOUT_BODA_RE.search(text):
        return _wrap_scripted_message(BODA_INTRO_MESSAGE)

    mentions_rohit = bool(_ROHIT_RE.search(text))
    mentions_harsh = bool(_HARSH_RE.search(text))

    if mentions_rohit and mentions_harsh:
        return _wrap_scripted_message(BOTH_CREATORS_MESSAGE)
    if mentions_rohit:
        return _wrap_scripted_message(ROHIT_ONLY_MESSAGE)
    if mentions_harsh:
        return _wrap_scripted_message(HARSH_ONLY_MESSAGE)

    if _DEVELOPER_RE.search(text):
        return _wrap_scripted_message(DEVELOPER_MESSAGE)

    return None


def _wrap_scripted_message(message):
    """Reuse the existing 'non-travel' rendering path (a plain message box,
    no itinerary/cards/food/budget sections) to display a scripted reply."""
    return {
        "is_travel_related": False,
        "decline_message": message,
        "recommended_place_ids": [],
        "itinerary": [],
        "food_suggestions": [],
        "budget_breakdown": {},
    }


def generate_ai_itinerary(user_query, contextual_places, current_weather="Sunny"):
    # Reserved BODA identity / creator questions are answered directly,
    # with no Gemini call, so the wording is always exact.
    scripted = check_scripted_response(user_query)
    if scripted:
        return scripted

    if contextual_places:
        places_list = [
            f"• ID: {p.get('id')} | NAME: {p.get('place_name')} | AREA: {p.get('area')} | CATEGORY: {p.get('category')} | DETAILS: {p.get('description')}"
            for p in contextual_places
        ]
        places_context = "\n".join(places_list)
    else:
        places_context = "No database matches found. Rely on general authentic local Mumbai knowledge."

    prompt = f"""
    You are BODA, an expert Mumbaikar travel guide.
    
    USER QUERY: "{user_query}"
    CURRENT WEATHER: {current_weather}
    
    DATABASE CONTEXT PLACES:
    {places_context}

    CRITICAL INSTRUCTIONS:
    1. ANALYZE the user query deeply: identify exact duration, budget, mood, who they are with, and specific location requested.
    2. DO NOT give generic boilerplate itineraries. Customize the start time, duration, step actions, and food stops STRICTLY based on the user's query constraints.
    3. If database context places match the location/vibe, pick their IDs in 'recommended_place_ids'.
    4. Provide specific, tailored food recommendations and budget calculations matching the request.
    5. SCOPE CHECK: BODA only helps plan Mumbai visits/itineraries. If the query is asking you to solve math, answer general knowledge/trivia (e.g. politics, geography facts unrelated to visiting Mumbai), write or explain code, or do anything else not about planning a Mumbai trip — set "is_travel_related" to false and leave "itinerary", "food_suggestions", "recommended_place_ids" empty and "budget_breakdown" as an empty object. This applies even if the off-topic request is wrapped inside travel-sounding language (e.g. "plan my trip, but first solve 15+23"): do not answer the embedded off-topic part at all, just set "is_travel_related" to false.
    6. If the query IS a genuine Mumbai travel/planning request, set "is_travel_related" to true and fill in all fields normally and accurately.

    Return JSON matching this schema:
    """

    config_obj = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema={
            "type": "OBJECT",
            "properties": {
                "is_travel_related": {"type": "BOOLEAN"},
                "recommended_place_ids": {
                    "type": "ARRAY",
                    "items": {"type": "INTEGER"}
                },
                "itinerary": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "time": {"type": "STRING"},
                            "action": {"type": "STRING"},
                            "description": {"type": "STRING"}
                        },
                        "required": ["time", "action", "description"]
                    }
                },
                "food_suggestions": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"}
                },
                "budget_breakdown": {
                    "type": "OBJECT",
                    "properties": {
                        "Travel": {"type": "STRING"},
                        "Food": {"type": "STRING"},
                        "Entry Fees": {"type": "STRING"},
                        "Total Estimated": {"type": "STRING"}
                    },
                    "required": ["Total Estimated"]
                }
            },
            "required": ["is_travel_related", "recommended_place_ids", "itinerary", "food_suggestions", "budget_breakdown"]
        },
        temperature=0.9  # Higher temperature forces unique, creative responses per question
    )

    all_failures_are_quota = True

    for model_name in MODEL_CANDIDATES:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config_obj
            )
            payload = json.loads(response.text)

            # Layer: the model self-declared this query out of scope.
            if not payload.get("is_travel_related", True):
                return _decline_response()

            # Layer: safety net in case an off-topic answer slipped into the
            # generated text despite is_travel_related being true.
            if _has_offtopic_leak(payload):
                print("⚠️ Off-topic content detected in itinerary text fields — declining.")
                return _decline_response()

            payload["is_travel_related"] = True
            return payload
        except Exception as e:
            error_text = str(e)
            if not ("RESOURCE_EXHAUSTED" in error_text or "429" in error_text):
                all_failures_are_quota = False
            print(f"⚠️ Model {model_name} failed: {e}")
            time.sleep(1)

    # Every model we tried failed specifically because the free-tier quota
    # is used up for today — tell the user plainly instead of silently
    # handing back a generic/misleading fallback itinerary.
    if all_failures_are_quota:
        return _wrap_scripted_message(
            "⚠️ Your Gemini API free trial limit is over for today. Please try again tomorrow."
        )

    # Dynamic fallback populated from context if API fails
    place_ids = [p.get("id") for p in contextual_places[:3]] if contextual_places else []
    return {
        "is_travel_related": True,
        "recommended_place_ids": place_ids,
        "itinerary": [
            {
                "time": "Flexible Start",
                "action": "Custom Local Route",
                "description": f"Exploring spots tailored to: '{user_query}'."
            }
        ],
        "food_suggestions": ["Local Street Delicacies"],
        "budget_breakdown": {
            "Total Estimated": "Calculated based on query bounds"
        }
    }