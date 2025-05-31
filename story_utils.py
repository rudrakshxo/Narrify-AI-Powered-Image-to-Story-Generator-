# story_utils.py

import re
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
from gtts import gTTS
from ctransformers import AutoModelForCausalLM
from deep_translator import GoogleTranslator
from gtts.lang import tts_langs  # Add this import

# === Load Models ===
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base", use_fast=True)
caption_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

llm = AutoModelForCausalLM.from_pretrained(
    "models\\openchat_3.5.Q4_K_M.gguf",
    model_type="llama",
    gpu_layers=0,
    max_new_tokens=256,
    temperature=0.7
)

# === Caption Generator ===
def generate_caption(image_path, language="en"):
    image = Image.open(image_path).convert('RGB')
    inputs = processor(images=image, return_tensors="pt")

    out = caption_model.generate(**inputs, max_length=40, num_beams=5, early_stopping=True)
    caption = processor.decode(out[0], skip_special_tokens=True)

    if language != "en":
        try:
            caption = GoogleTranslator(source='en', target=language).translate(caption)
        except Exception as e:
            print(f"[Translation] Caption translation failed: {e}")
            # fallback to English
    return caption

# === Story or Description Generator ===
def generate_story(caption, max_tokens=256, mode="story", language="en"):
    if mode == "description":
        prompt = (
            "You are an expert in visual scene interpretation. Based on the image caption provided, "
            "write a clear and factual visual description. Stay strictly under 200 words. "
            "Only describe what can be visually inferred — do not speculate or add imaginary details."
            "Do not write anything other than the detailed description"
            f"\n\nImage Caption: \"{caption}\"\n\nVisual Description:"
        )
    else:
        prompt = (
            "You are a brilliant and concise storyteller. Write a complete short story based on the image caption below. "
            "The story must have a beginning, middle, and end. Limit your response to 200 words or fewer (around 3 short paragraphs)."
            "Do not write anything other than the story"
            f"\n\nImage Caption: \"{caption}\"\n\nShort Story:"
        )

    try:
        raw_output = llm(prompt, max_new_tokens=max_tokens)
        story = clean_story(raw_output)
    except Exception as e:
        print(f"[LLM Error] Failed to generate: {e}")
        return "⚠️ Sorry, generation failed."

    if language != "en":
        try:
            story = GoogleTranslator(source='en', target=language).translate(story)
        except Exception as e:
            print(f"[Translation Error] Translation failed: {e}")

    return story


# === Voice Narrator ===
def speak_story(text, path="output.wav", language="en"):
    try:
        if language not in tts_langs():
            print(f"[TTS] Language '{language}' not supported by gTTS. Defaulting to English.")
            language = "en"
        tts = gTTS(text=text, lang=language, tld="com")
        tts.save(path)
        return path
    except Exception as e:
        print(f"[TTS Error] gTTS failed: {e}")
        return None


# === Clean LLM Output ===
def clean_story(text):
    cleaned = re.sub(r"<\|.*?\|>", "", text)
    cleaned = re.sub(r"[\|<>]+", "", cleaned)
    return cleaned.strip()
