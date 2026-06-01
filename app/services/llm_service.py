import os
import requests
from typing import Any, Optional
from google import genai
from google.genai import types
from app.core.config import get_settings

settings = get_settings()

class LLMGenerationService:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self.gemini_api_key = getattr(settings, "GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
        self.gemini_model = settings.GEMINI_MODEL
        self.ollama_url = settings.OLLAMA_URL
        self.ollama_model = settings.OLLAMA_MODEL
        
        self.max_tokens = getattr(settings, "LLM_MAX_TOKENS", 1024)
        self.timeout = getattr(settings, "LLM_REQUEST_TIMEOUT", 30)

        self.genai_client = None
        if self.provider == "gemini" and self.gemini_api_key:
            self.genai_client = genai.Client(api_key=self.gemini_api_key)

    def synthesize_answer(self, question: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        if not chunks:
            return {
                "answer": "I cannot answer this question because no audited corporate records were retrieved.",
                "citations": []
            }

        context_blocks = []
        citations = []
        for index, chunk in enumerate(chunks, start=1):
            text = chunk.get("text", "").strip()
            doc_id = chunk.get("metadata", {}).get("document_id", "Unknown-Doc")
            chunk_id = chunk.get("point_id", f"chk-{index}")
            
            context_blocks.append(f"[Source ID: {index} | Document: {doc_id}]\nContent: {text}\n")
            citations.append({
                "source_index": index,
                "document_id": doc_id,
                "point_id": chunk_id,
                "snippet_preview": text[:100] + "..."
            })

        formatted_context = "\n---\n".join(context_blocks)

        system_instruction = (
            "You are a strict enterprise compliance assistant. Your sole task is to answer "
            "the user's question using exclusively the audited text snippets provided in the 'Context' section. "
            "Adhere to these absolute safety rules:\n"
            "1. Your answer must be factual, direct, and completely derived from the provided context.\n"
            "2. If the context does not contain explicit, undeniable evidence to answer the question, "
            "state verbatim: 'I cannot verify this information using audited corporate records.'\n"
            "3. Do not assume, extrapolate, or combine outside knowledge.\n"
            "4. For every claim you make, append the corresponding source citation marker at the end of the sentence "
            "matching the format [Source ID: X]."
        )

        user_prompt = f"Context:\n{formatted_context}\n\nQuestion: {question}"

        try:
            if self.provider == "gemini" and self.genai_client:
                return self._generate_via_gemini(system_instruction, user_prompt, citations)
            else:
                return self._generate_via_ollama(system_instruction, user_prompt, citations)
        except Exception as e:
            return {
                "answer": f"Generation layer encountered an infrastructure exception: {str(e)}",
                "citations": citations,
                "error": True
            }

    def _generate_via_gemini(self, system_prompt: str, user_prompt: str, citations: list[dict]) -> dict[str, Any]:
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.0,
            max_output_tokens=self.max_tokens
        )
        
        response = self.genai_client.models.generate_content(
            model=self.gemini_model,
            contents=user_prompt,
            config=config
        )
        
        answer_text = ""
        if response.text:
            answer_text = response.text.strip()
        elif response.candidates and response.candidates[0].content.parts:
            answer_text = response.candidates[0].content.parts[0].text.strip()
        else:
            answer_text = "I cannot verify this information due to generation safety restrictions."

        return {
            "answer": answer_text,
            "citations": citations,
            "provider": self.gemini_model
        }

    def _generate_via_ollama(self, system_prompt: str, user_prompt: str, citations: list[dict]) -> dict[str, Any]:
        payload = {
            "model": self.ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.0
            }
        }
        
        response = requests.post(self.ollama_url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        result_text = response.json().get("message", {}).get("content", "").strip()
        
        return {
            "answer": result_text,
            "citations": citations,
            "provider": f"ollama-{self.ollama_model}"
        }