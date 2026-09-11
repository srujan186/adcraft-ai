import os 
import json
import re
from groq import Groq
from dotenv import load_dotenv


load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Groq retired llama-3.3-70b-versatile (404 model_not_found). Chosen by
# benchmarking the candidates this key can reach against the real build_prompt():
# gpt-oss-120b held ~73% of the 30s word target (qwen3.8-27b sat at 43% — always
# ~35 words regardless of duration, i.e. half a 30s ad is silence).
# Costs ~3.6k tokens/script against an 8k TPM ceiling: roughly 2 scripts/minute.
MODEL = "openai/gpt-oss-120b"

STYLE_DESCRIPTIONS = {
    "modern": (
        "Clean, confident, and aspirational. "
        "Professional tone. Premium feel. "
        "Short punchy sentences. No fluff."
    ),
    "bold": (
        "High energy, exciting, powerful. "
        "Big claims. Strong action words. "
        "Creates urgency and excitement."
    ),
    "minimal": (
        "Ultra simple. One powerful idea. "
        "As few words as possible. "
        "Every word must earn its place."
    ),
    "playful": (
        "Fun, friendly, warm, approachable. "
        "Light-hearted tone. "
        "Makes people smile."
    ),
}

def build_prompt(
    business_name: str,
    description:   str,
    tagline:       str,
    ad_style:      str,
    duration:      int
) -> str:

    """
    Builds a detailed prompt for the AI.

    Why such a specific prompt?
    The more specific we are, the better the output.
    We tell the AI:
    - WHO the business is
    - WHAT style we want
    - EXACTLY what format to return
    - HOW LONG the voiceover should be

    The JSON format instruction is critical —
    without it, AI returns prose we can't parse.
    """

    style_desc = STYLE_DESCRIPTIONS.get(
        ad_style,
        STYLE_DESCRIPTIONS["modern"]
    )

    # Word count target
    # Kokoro is synthesized at speed=1.3x (set in tts.py).
    # At 1.3x, effective rate ≈ 2.6 words/sec.
    # Target ~40 words for 15s | ~80 words for 30s — fills 4 proper sentences.
    target_words = int(duration * 2.7)   # ideal centre (40 for 15s, 81 for 30s)
    min_words    = int(duration * 2.5)   # absolute minimum (37 for 15s)
    max_words    = int(duration * 3.0)   # hard ceiling (45 for 15s)

    prompt = f"""You are a senior creative director at a world-class ad agency.
You have written campaigns for Apple, Nike, Airbnb, and Coca-Cola.
Your voiceovers sound like REAL TV and YouTube ads — never robotic, never generic.

BUSINESS:
- Name: {business_name}
- Description: {description}
- Tagline: {tagline or "None"}
- Ad Style: {ad_style} — {style_desc}
- Ad Duration: {duration} seconds

YOUR TASK:
Write a complete {duration}-second video ad script for {business_name}.

━━━ VOICEOVER — MOST IMPORTANT FIELD ━━━
The voiceover MUST be between {min_words} and {max_words} words. Ideal: {target_words} words.

⚠️  CRITICAL: the script must END NATURALLY and feel COMPLETE within the word limit.
- The final line must be a clean brand landing or CTA — not a trailing thought.
- Do NOT write more than {max_words} words or the audio will be cut off mid-sentence.
- Every word must earn its place. No padding. No filler.

STRUCTURE — write EXACTLY 4 complete sentences (not fragments):
1. HOOK sentence (8-10 words) — open with a relatable problem or bold claim
2. CONTEXT sentence (10-12 words) — explain what {business_name} does and who it's for
3. BENEFIT sentence (10-12 words) — the key result, outcome, or unique advantage it delivers
4. LAND sentence (6-8 words) — brand name + strong call to action

HOW REAL ADS SOUND — match this quality:
✅ TARGET (~40 words, 4 sentences):
"Running a business is hard enough. {business_name} gives you the tools, the insights, and the support to grow — without the guesswork. Thousands of businesses already trust us to get it done. Start your free trial today."

✅ ANOTHER EXAMPLE (~38 words):
"Your customers expect more. {business_name} helps you deliver faster service, smarter workflows, and a better experience — every single time. Built for teams that refuse to settle. Join us and see the difference."

❌ BAD (fragments, too short, no real info):
"You fast but motion go faster. Try it free now!" — This is NOT acceptable.

- Each sentence must be a complete thought, not a one-word fragment.
- Include real detail about what the brand does, not generic puffery.
- Mention the brand name exactly once, in sentence 4.
- No filler: "In today's world", "Look no further", "A wide range of solutions"

━━━ OTHER FIELDS ━━━
Headline: max 8 words, punchy and memorable
Subtext: max 15 words, one clear value statement
CTA: max 4 words, strong verb + outcome (e.g. "Start Free Today")
Music: choose ONE that fits the tone: upbeat, calm, corporate, dramatic, inspirational
Scene: 2-3 vivid visual scenes for the video background (one sentence each)
Color mood: ONE of: vibrant, dark, light, warm, cool
Key message: ONE sentence — the single idea viewers must remember

RETURN ONLY THIS JSON — no markdown, no explanation, nothing else:
{{
    "headline":          "...",
    "subtext":           "...",
    "cta":               "...",
    "voiceover":         "...",
    "music_style":       "upbeat",
    "scene_description": "Scene 1: ... Scene 2: ... Scene 3: ...",
    "color_mood":        "vibrant",
    "key_message":       "..."
}}"""

    
    return prompt



def parse_ai_response(response_text: str) -> dict:
    """
    Parses the AI's text response into a Python dictionary.

    Why do we need this?
    Even when we say "return only JSON", AI sometimes adds:
    - ```json ... ``` markdown fences
    - "Here is the JSON:" prefix text
    - Trailing explanation text

    This function handles all those cases robustly.
    """
    text = response_text.strip()

    # Remove markdown code fences if present
    # ```json ... ``` or ``` ... ```
    if "```" in text:
        # Extract content between first ``` and last ```
        parts = text.split("```")
        # parts[0] = before first ```
        # parts[1] = content (might start with "json")
        # parts[2] = after last ```
        if len(parts) >= 3:
            text = parts[1]
            # Remove "json" language identifier if present
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

    # Find JSON object — look for first { and last }
    # This handles any text before or after the JSON
    start = text.find("{")
    end   = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError(
            f"No JSON object found in AI response: {text[:200]}"
        )

    json_str = text[start:end + 1]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Failed to parse JSON from AI response: {e}\n"
            f"JSON string was: {json_str[:300]}"
        )


def validate_script(script: dict, business_name: str) -> dict:
    """
    Validates the AI response has all required fields.
    Fills in sensible defaults for any missing fields.

    Why validate?
    AI can sometimes miss a field or return wrong types.
    We never want the app to crash because AI forgot a field.
    Defaults ensure the pipeline always continues.
    """

    defaults = {
        "headline":          f"Discover {business_name}",
        "subtext":           "Quality you can trust",
        "cta":               "Learn More",
        "voiceover":         f"Discover what {business_name} has to offer.",
        "music_style":       "upbeat",
        "scene_description": "Modern professional workspace with people collaborating",
        "color_mood":        "vibrant",
        "key_message":       f"{business_name} — excellence in every detail",
    }
    
    valid_music_styles = [
        "upbeat", "calm", "corporate",
        "dramatic", "inspirational"
    ]
    valid_color_moods = [
        "vibrant" , "dark", "light" , "warm", "cool"
    ]


    for field , default in defaults.items():
        if field not in script or not script[field]:
            print(f" Missing field '{field}' - using default")
            script[field] = default


    if script["music_style"] not in valid_music_styles:
        print(f"invalid music_style:{script['music_style']} -- using 'upbeat' ")
        script["music_style"] = "upbeat"


    if script["color_mood"] not in valid_color_moods:
        print(f"  ⚠️ Invalid color_mood: {script['color_mood']} — using 'vibrant'")
        script["color_mood"] = "vibrant"

    
        # Enforce length limits
    # Truncate if AI exceeded limits
    headline_words = script["headline"].split()
    if len(headline_words) > 10:
        script["headline"] = " ".join(headline_words[:10])
        print(f"  ⚠️ Headline truncated to 10 words")

    cta_words = script["cta"].split()
    if len(cta_words) > 5:
        script["cta"] = " ".join(cta_words[:5])
        print(f"  ⚠️ CTA truncated to 5 words")

    return script



async def generate_ad_script(
    business_name: str,
    description:   str,
    tagline:       str = "",
    ad_style:      str = "modern",
    duration:      int = 15
) -> dict:

    """
    Main function — generates a complete ad script using Groq AI.

    Flow:
    1. Build prompt from brand data
    2. Send to Groq API (see MODEL)
    3. Parse JSON response
    4. Validate all fields
    5. Return clean script dictionary

    Why async?
    Groq API call takes 1-3 seconds.
    async means FastAPI can handle other requests during that wait.
    """

    print(f"\n🤖 Generating ad script for: {business_name}")
    print(f"   Style: {ad_style} | Duration: {duration}s")
    print("─" * 50)

    # Step 1: Build the prompt
    prompt = build_prompt(
        business_name=business_name,
        description=description,
        tagline=tagline,
        ad_style=ad_style,
        duration=duration
    )

    print(f"Prompt built ({len(prompt)} chars)")


    try:
        print(" calling Groq api ...")


        # Note: Groq's Python client is synchronous
        # We call it directly — FastAPI handles this fine
        # for moderate traffic

        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a world-class advertising creative director with 20 years of experience "
                        "writing TV commercials, YouTube pre-rolls, and digital video ads for global brands. "
                        "Your scripts are emotionally resonant, brand-specific, and sound like REAL ads — "
                        "not generic marketing copy. "
                        "You always return valid JSON only. Never include markdown, explanations, "
                        "or any text outside the JSON object."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.75,
            # gpt-oss models emit reasoning tokens *before* the answer, and
            # those count against this budget. At 1200 the JSON came back
            # truncated or empty, which parse_ai_response treats as fatal.
            max_tokens=4000,
            # Groq's JSON mode. parse_ai_response still runs — this just stops
            # it being the only thing between us and a 500.
            response_format={"type": "json_object"},
        )


        response_text = completion.choices[0].message.content
        print(f"Groq respond ({len(response_text)} chars)")
        print(f"Tokens used: {completion.usage.total_tokens}")

    except Exception as e:
        raise Exception(f"Groq API call failed: {str(e)}")


    # Step 3: Parse the JSON response
    try:
        print("🔍 Parsing AI response...")
        script = parse_ai_response(response_text)
        print("✅ JSON parsed successfully")

    except ValueError as e:
        print(f"❌ Parse failed: {e}")
        print(f"   Raw response: {response_text[:300]}")
        raise Exception(f"Failed to parse AI response: {str(e)}")

    # Step 4: Validate all fields
    print("✅ Validating script fields...")
    script = validate_script(script, business_name)

    # Step 5: Log the result
    print(f"\n📋 Generated Script:")
    print(f"   Headline:    {script['headline']}")
    print(f"   Subtext:     {script['subtext']}")
    print(f"   CTA:         {script['cta']}")
    print(f"   Music:       {script['music_style']}")
    print(f"   Voiceover:   {script['voiceover'][:80]}...")
    print(f"   Key message: {script['key_message']}")

    return script
