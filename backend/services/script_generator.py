import os 
import json
import re
from groq import Groq
from dotenv import load_dotenv


load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "llama-3.3-70b-versatile"

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

    style_desc =STYLE_DESCRIPTIONS.get(
        ad_style,
        STYLE_DESCRIPTIONS["modern"]
    )

    # Calculate voiceover word count
    # Average speaking pace = 2.5 words per second
    # We use 2.3 to leave breathing room
    max_words    = int(duration * 2.3)
    min_words    = int(duration * 1.8)

    prompt = f"""You are an award-winning advertising copywriter.
Your ads are concise, emotionally compelling, and drive action.

BUSINESS INFORMATION:
- Name: {business_name}
- Description: {description}
- Tagline: {tagline or "Not provided"}
- Ad Style: {ad_style} — {style_desc}
- Ad Duration: {duration} seconds

YOUR TASK:
Write a {duration}-second video advertisement for {business_name}.

STRICT RULES:
1. Headline: maximum 8 words, must be memorable and punchy
2. Subtext: maximum 15 words, explains the value clearly
3. CTA: maximum 4 words, strong action verb (e.g. "Start Free Today")
4. Voiceover: MUST be between {min_words} and {max_words} words
   Natural conversational speech, not formal or robotic
5. Music: choose ONE from: upbeat, calm, corporate, dramatic, inspirational
6. Scene: describe 2-3 visual scenes for video background (one sentence each)
7. Color mood: choose ONE from: vibrant, dark, light, warm, cool
8. Key message: ONE sentence — the single thing viewers must remember

RETURN ONLY THIS JSON — no markdown, no explanation, nothing else:
{{
    "headline":          "your headline here",
    "subtext":           "your subtext here",
    "cta":               "your cta here",
    "voiceover":         "your full voiceover script here",
    "music_style":       "upbeat",
    "scene_description": "Scene 1: ... Scene 2: ... Scene 3: ...",
    "color_mood":        "vibrant",
    "key_message":       "your key message here"
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
    2. Send to Groq API (Llama 3.3 70B)
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
                    "role":    "system",
                    "content": (
                        "You are an expert advertising copywriter. "
                        "You always return valid JSON only. "
                        "Never include markdown, explanations, or "
                        "any text outside the JSON object."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
                        # temperature controls creativity:
            # 0.0 = very predictable, always same answer
            # 0.7 = balanced (creative but focused)
            # 1.0 = very creative but sometimes random

            max_tokens=1000,
            # max_tokens limits response length
            # 1000 is enough for our JSON script
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
