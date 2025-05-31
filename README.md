# Narrify-AI-Powered-Image-to-Story-Generator-
Narrify is a full-stack AI web app that transforms images into narrated stories or descriptions using state-of-the-art open-source models. Built with a custom UI in Flask, Narrify blends vision, language, and voice into one seamless experience.
---

## 🚀 Features

- 🖼️ **Image Upload Interface** – Upload any image from your device
- 📷 **Caption Generation** – Powered by BLIP (Hugging Face)
- ✍️ **Story or Description Creation** – Using OpenChat 3.5 LLM via `ctransformers`
- 🌍 **Multilingual Output** – Hindi, Spanish, French, German, Japanese, and more
- 🔊 **Narration with gTTS** – Real-time audio generation of the story/description
- 🔐 **User Authentication** – Register/login with OTP email verification
- 🧠 **Secure Password Reset** – Reset password via dashboard with OTP
- 📜 **Story History** – Logged-in users can see and revisit their past stories
- 💅 **Animated UI** – Blur effects, glowing buttons, and cyberpunk visuals

---

## 🛠️ Tech Stack

| Layer       | Tech                                             |
|-------------|--------------------------------------------------|
| Backend     | Python, Flask, SQLite, Flask-Login               |
| AI Models   | BLIP (Salesforce), OpenChat 3.5 (GGUF), gTTS     |
| UI/UX       | Jinja2 Templates, Bootstrap 5, custom CSS        |
| TTS         | `gTTS` (Google Text-to-Speech)                   |
| Translation | `deep-translator` (Google Translate wrapper)     |

---
