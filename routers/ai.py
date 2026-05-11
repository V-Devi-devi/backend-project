import os
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dependencies import get_current_user

router = APIRouter(prefix="/ai", tags=["AI"])

if not os.getenv("GEMINI_API_KEY"):
    raise RuntimeError("GEMINI_API_KEY is not set in .env")

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-2.5-flash"

GENERATION_CONFIG = types.GenerateContentConfig(
    temperature=0.7,
    max_output_tokens=512
)

SYSTEM_CONTEXT = (
    "You are a helpful Python programming assistant for college students. "
    "Answer questions about Python, web development, FastAPI, React, databases, and AI. "
    "Keep responses under 200 words unless more detail is required."
)

chat_sessions: Dict[int, object] = {}

def get_or_create_session(user_id: int):
    if user_id not in chat_sessions:
        chat_sessions[user_id] = client.chats.create(
            model=MODEL_NAME,
            history=[
                {
                    "role": "user",
                    "parts": [{"text": SYSTEM_CONTEXT}]
                },
                {
                    "role": "model",
                    "parts": [{"text": "Understood. Ready to help."}]
                }
            ]
        )
    return chat_sessions[user_id]

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)

class ChatResponse(BaseModel):
    reply: str

class SummariseRequest(BaseModel):
    text: str = Field(min_length=20, max_length=5000)
    max_words: int = Field(default=150, ge=30, le=500)

class SummariseResponse(BaseModel):
    summary: str

@router.post("/chat", response_model=ChatResponse)
def chat_with_ai(
    request: ChatRequest,
    current_user=Depends(get_current_user),
):
    session = get_or_create_session(current_user.id)

    try:
        response = session.send_message(request.message)

        return ChatResponse(
            reply=response.text.strip()
        )

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Message could not be processed. Try rephrasing."
        )

    except Exception as exc:
        print(f"[chat] Gemini error: {exc}")

        raise HTTPException(
            status_code=503,
            detail="AI service unavailable."
        )

@router.post("/summarize", response_model=SummariseResponse)
def summarize_text(
    request: SummariseRequest,
    current_user=Depends(get_current_user),
):
    prompt = (
        f"Summarise the following text in no more than "
        f"{request.max_words} words. "
        f"Return only the summary without headings or commentary.\n\n"
        f"TEXT:\n{request.text}"
    )

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=600
            )
        )

        return SummariseResponse(
            summary=response.text.strip()
        )

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Content could not be processed."
        )

    except Exception as exc:
        print(f"[summarize] Gemini error: {exc}")

        raise HTTPException(
            status_code=503,
            detail="AI service unavailable."
        )

@router.delete("/chat/reset", status_code=204)
def reset_chat(
    current_user=Depends(get_current_user)
):
    chat_sessions.pop(current_user.id, None)

    return Response(status_code=204)