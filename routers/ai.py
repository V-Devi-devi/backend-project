import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, Field
from typing import Literal
from google import genai
from google.genai import types
import json

from dependencies import get_current_user

router = APIRouter(prefix="/ai", tags=["AI"])
if not os.getenv("GEMINI_API_KEY"):
    raise RuntimeError("GEMINI_API_KEY is not set in .env")

client = genai.Client() 

MODEL_NAME = "gemini-3.1-flash-lite"
GENERATION_CONFIG = types.GenerateContentConfig(
    temperature=0.7,
    max_output_tokens=512,
)
SYSTEM_CONTEXT = """You are a Python and full stack development tutor
for college students who are new to programming.

Response rules:
- Start with a simple real-world analogy before the technical explanation
- Use a short, runnable Python code example when relevant (under 10 lines)
- Keep answers under 200 words unless the question genuinely needs more
- If asked about something outside Python or web development, respond:
  "I am a programming assistant — please ask a Python or web development question."
- Never use jargon without immediately explaining it

The student is learning: Python, FastAPI, React, SQLite, and basic AI.
Their experience level: beginner, first programming course."""

chat_sessions: dict[int, object] = {}

def get_or_create_session(user_id: int):
    if user_id not in chat_sessions:
        chat_sessions[user_id] = client.chats.create(
            model=MODEL_NAME,
            history=[
                {"role": "user",  "parts": [{"text": SYSTEM_CONTEXT}]},
                {"role": "model", "parts": [{"text": "Understood. Ready to help."}]},
            ]
        )
    return chat_sessions[user_id]

# ── Generator that yields SSE-formatted chunks ───────────────────────
def stream_chat_response(user_id: int, message: str):
    """
    Generator: yields SSE events as Gemini produces tokens.
    Uses the user's existing ChatSession so history is maintained.
    """
    session = get_or_create_session(user_id)
    try:
        for chunk in session.send_message_stream(message):
            if chunk.text:
                data = json.dumps({"chunk": chunk.text})
                yield f"data: {data}\n\n"
        yield "data: [DONE]\n\n"

    except ValueError:
        error = json.dumps({"error": "Content blocked — try rephrasing."})
        yield f"data: {error}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as exc:
        print(f"[stream] Gemini error: {exc}")
        error = json.dumps({"error": "AI service temporarily unavailable."})
        yield f"data: {error}\n\n"
        yield "data: [DONE]\n\n"

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)

class ChatResponse(BaseModel):
    reply: str

class SummariseRequest(BaseModel):
    text: str = Field(min_length=20, max_length=5000)
    max_words: int = Field(default=150, ge=30, le=500)

class SummariseResponse(BaseModel):
    summary: str

class ExplainRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=300)
    level: Literal["beginner", "intermediate", "expert"] = "beginner"

class ExplainResponse(BaseModel):
    explanation: str

class StreamRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)

LEVEL_PERSONAS = {
    "beginner":     "a school student who has never programmed before",
    "intermediate": "a college student who knows Python basics",
    "expert":       "a senior software engineer who wants implementation details",
}

@router.post("/chat", response_model=ChatResponse)
def chat_with_ai(
    request: ChatRequest,
    current_user=Depends(get_current_user),
):
    session = get_or_create_session(current_user.id)
    try:
        response = session.send_message(request.message)
        return ChatResponse(reply=response.text.strip())
    except ValueError:
        raise HTTPException(status_code=400,
                            detail="Message could not be processed — try rephrasing.")
    except Exception as exc:
        print(f"[chat] Gemini error: {exc}")
        raise HTTPException(status_code=503, detail="AI service unavailable.")

@router.post("/summarize", response_model=SummariseResponse)
def summarize_text(
    request: SummariseRequest,
    current_user=Depends(get_current_user),
):
    prompt = (
        f"Summarise the following text in no more than {request.max_words} words. "
        f"Return only the summary — no headings, no preamble, no commentary.\n\n"
        f"TEXT:\n{request.text}"
    )
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.3, max_output_tokens=600),
        )
        return SummariseResponse(summary=response.text.strip())
    except ValueError:
        raise HTTPException(status_code=400, detail="Content could not be processed.")
    except Exception as exc:
        print(f"[summarize] Gemini error: {exc}")
        raise HTTPException(status_code=503, detail="AI service unavailable.")

@router.delete("/chat/reset", status_code=204)
def reset_chat(current_user=Depends(get_current_user)):
    chat_sessions.pop(current_user.id, None)
    return Response(status_code=204)

@router.post("/explain", response_model=ExplainResponse)
def explain_topic(
    request: ExplainRequest,
    current_user=Depends(get_current_user),
):
    persona = LEVEL_PERSONAS[request.level]
    prompt = (
        f"Explain the following to {persona}.\n"
        f"Include a real-world analogy. "
        f"If relevant, add a short Python code example (5 lines max).\n"
        f"Keep the explanation under 200 words.\n\n"
        f"TOPIC: {request.topic}"
    )
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=GENERATION_CONFIG,
        )
        return ExplainResponse(explanation=response.text.strip())
    except ValueError:
        raise HTTPException(status_code=400, detail="Content could not be processed.")
    except Exception as exc:
        print(f"[explain] Gemini error: {exc}")
        raise HTTPException(status_code=503, detail="AI service unavailable.")
    

# ── POST /ai/stream ──────────────────────────────────────────────────
@router.post("/stream")
def stream_ai_response(
    request: StreamRequest,
    current_user=Depends(get_current_user),
):
    return StreamingResponse(
        stream_chat_response(current_user.id, request.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",    # prevents nginx from buffering chunks
        }
    )