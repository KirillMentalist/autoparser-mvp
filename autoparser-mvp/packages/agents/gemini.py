import os, json
from typing import Dict, Any
from google import genai
from google.genai import types
from .prompt_loader import render_prompt

class GeminiClient:
    def __init__(self, api_key: str | None = None, model: str | None = None, vertexai: bool | None = None):
        api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
        # If running against Vertex AI (Express mode), pass vertexai=True, else False for Developer API
        vtx_flag = vertexai if vertexai is not None else bool(os.getenv("GOOGLE_GENAI_USE_VERTEXAI"))
        if api_key and not vtx_flag:
            self.client = genai.Client(api_key=api_key)  # Developer API
        else:
            # Vertex AI uses ADC or env flags; if vertexai=True no api_key is needed here
            if vtx_flag and api_key:
                self.client = genai.Client(vertexai=True, api_key=api_key)
            else:
                self.client = genai.Client(vertexai=vtx_flag)

    def run_stage(self, stage: str, prompt_name: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        # Render the Markdown prompt with variables
        prompt = render_prompt(prompt_name, variables).get("rendered", "")
        cfg = types.GenerateContentConfig(
            response_mime_type="application/json",  # ask Gemini for JSON
            temperature=float(os.getenv("GEMINI_TEMPERATURE","0.1"))
        )
        resp = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=cfg
        )
        # Prefer resp.text() quick accessor if present; fallback to candidates
        try:
            text = resp.text  # new SDK exposes property
        except Exception:
            text = getattr(resp, "text", None) or ""
        if not text:
            # fallback: try first candidate
            try:
                cand = resp.candidates[0]
                text = "".join(getattr(p, "text", "") for p in cand.content.parts)
            except Exception:
                text = ""
        # Try to parse JSON
        try:
            return json.loads(text)
        except Exception:
            # Last resort: try to find JSON blob within text
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start:end+1])
                except Exception:
                    pass
            raise ValueError(f"Non-JSON response for {stage}: {text[:500]}")
