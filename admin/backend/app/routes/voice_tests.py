"""
Voice testing API routes.

Provides testing endpoints for STT, TTS, LLM, RAG, and full pipeline tests.
Adapted for Mac Studio/mini architecture (no Jetson wake word detection).
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
import structlog
import aiohttp
import time
import os
import uuid

from app.database import get_db
from app.auth.oidc import get_current_user
from app.models import User, VoiceTest

logger = structlog.get_logger()

router = APIRouter(prefix="/api/voice-tests", tags=["voice-tests"])


class TestQuery(BaseModel):
    """Request model for test queries."""
    text: str = None
    model: str = None
    voice: str = None
    connector: str = None


@router.post("/stt/test")
async def test_speech_to_text(
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Test Wyoming Whisper STT service on Mac Studio (192.168.10.167:10300).

    Uploads audio file and transcribes using Faster-Whisper.
    """
    if not current_user.has_permission('write'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Save uploaded audio
    audio_path = f"/tmp/test_audio_{uuid.uuid4()}.wav"
    try:
        with open(audio_path, "wb") as f:
            f.write(await audio.read())

        # Call Wyoming STT service (simplified - actual Wyoming protocol would use websockets)
        # For now, we'll simulate the call
        start = time.time()

        # TODO: Implement actual Wyoming protocol call
        # This is a placeholder that would need Wyoming client library
        transcript = "Sample transcript (Wyoming STT not yet implemented)"
        confidence = 0.95

        elapsed = time.time() - start

        result = {
            "transcript": transcript,
            "confidence": confidence,
            "processing_time": int(elapsed * 1000),
            "model": "faster-whisper-tiny.en",
            "service": "mac-studio-whisper"
        }

        # Store test result
        test = VoiceTest(
            test_type="stt",
            test_input=audio.filename,
            test_config={"audio_file": audio.filename},
            result=result,
            success=True,
            executed_by_id=current_user.id
        )
        db.add(test)
        db.commit()

        logger.info("stt_test_completed", user=current_user.username, success=True)

        return {
            "success": True,
            **result
        }

    except Exception as e:
        logger.error("stt_test_failed", error=str(e))

        # Store failure
        test = VoiceTest(
            test_type="stt",
            test_input=audio.filename,
            test_config={"audio_file": audio.filename},
            result={},
            success=False,
            error_message=str(e),
            executed_by_id=current_user.id
        )
        db.add(test)
        db.commit()

        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Cleanup
        if os.path.exists(audio_path):
            os.remove(audio_path)


@router.post("/tts/test")
async def test_text_to_speech(
    query: TestQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Test Wyoming Piper TTS service on Mac Studio (192.168.10.167:10200).

    Generates audio from text using Piper TTS.
    """
    if not current_user.has_permission('write'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    if not query.text:
        raise HTTPException(status_code=400, detail="Text is required")

    try:
        start = time.time()

        # TODO: Implement actual Wyoming protocol call for TTS
        # This is a placeholder
        audio_path = f"/tmp/tts_output_{uuid.uuid4()}.wav"

        # Simulate TTS generation
        elapsed = time.time() - start

        result = {
            "audio_path": audio_path,
            "text": query.text,
            "voice": query.voice or "default",
            "processing_time": int(elapsed * 1000),
            "model": "piper-tts",
            "service": "mac-studio-piper"
        }

        # Store test result
        test = VoiceTest(
            test_type="tts",
            test_input=query.text,
            test_config={"voice": query.voice},
            result=result,
            success=True,
            executed_by_id=current_user.id
        )
        db.add(test)
        db.commit()

        logger.info("tts_test_completed", user=current_user.username, success=True)

        return {
            "success": True,
            **result,
            "note": "Wyoming TTS protocol not yet implemented - placeholder response"
        }

    except Exception as e:
        logger.error("tts_test_failed", error=str(e))

        test = VoiceTest(
            test_type="tts",
            test_input=query.text,
            test_config={"voice": query.voice},
            result={},
            success=False,
            error_message=str(e),
            executed_by_id=current_user.id
        )
        db.add(test)
        db.commit()

        raise HTTPException(status_code=500, detail=str(e))


@router.post("/llm/test")
async def test_llm_processing(
    query: TestQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Test Ollama LLM on Mac Studio (192.168.10.167:11434).

    Processes prompt using Phi-3 or Llama 3.1 models.
    """
    if not current_user.has_permission('write'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    if not query.text:
        raise HTTPException(status_code=400, detail="Prompt is required")

    model = query.model or "phi3:mini"

    try:
        url = "http://192.168.10.167:11434/api/generate"
        payload = {
            "model": model,
            "prompt": query.text,
            "stream": False
        }

        start = time.time()
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                elapsed = time.time() - start
                if resp.status == 200:
                    data = await resp.json()
                    # Sanitize Unicode characters to prevent DB encoding issues
                    response_text = data.get("response", "")
                    response_text = response_text.replace('\u2018', "'").replace('\u2019', "'")  # Smart single quotes
                    response_text = response_text.replace('\u201c', '"').replace('\u201d', '"')  # Smart double quotes
                    response_text = response_text.replace('\u2013', '-').replace('\u2014', '-')  # En/Em dashes

                    result = {
                        "response": response_text,
                        "processing_time": int(elapsed * 1000),
                        "model": model,
                        "tokens": data.get("eval_count", 0),
                        "tokens_per_second": round(data.get("eval_count", 0) / elapsed, 2) if elapsed > 0 else 0,
                        "service": "mac-studio-ollama"
                    }

                    # Store test result
                    test = VoiceTest(
                        test_type="llm",
                        test_input=query.text,
                        test_config={"model": model},
                        result=result,
                        success=True,
                        executed_by_id=current_user.id
                    )
                    db.add(test)
                    db.commit()

                    logger.info("llm_test_completed", model=model, user=current_user.username, success=True)

                    return {
                        "success": True,
                        **result
                    }
                else:
                    error_text = await resp.text()
                    raise Exception(f"HTTP {resp.status}: {error_text}")

    except Exception as e:
        logger.error("llm_test_failed", error=str(e))

        test = VoiceTest(
            test_type="llm",
            test_input=query.text,
            test_config={"model": model},
            result={},
            success=False,
            error_message=str(e),
            executed_by_id=current_user.id
        )
        db.add(test)
        db.commit()

        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag/test")
async def test_rag_query(
    query: TestQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Test RAG service with query.

    Tests weather, airports, or sports RAG connectors.
    """
    if not current_user.has_permission('write'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    if not query.text:
        raise HTTPException(status_code=400, detail="Query is required")

    connector = query.connector or "weather"

    try:
        # Determine RAG service URL
        port_map = {
            "weather": 8010,
            "airports": 8011,
            "flights": 8012
        }
        port = port_map.get(connector, 8010)

        # Build URL based on connector type
        if connector == "weather":
            url = f"http://192.168.10.167:{port}/weather/current?location={query.text}"
        elif connector == "airports":
            url = f"http://192.168.10.167:{port}/airports/{query.text}"
        elif connector == "flights":
            url = f"http://192.168.10.167:{port}/flights/{query.text}"
        else:
            raise HTTPException(status_code=400, detail=f"Unknown connector: {connector}")

        start = time.time()
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                elapsed = time.time() - start
                if resp.status == 200:
                    data = await resp.json()
                    result = {
                        "response": data,
                        "processing_time": int(elapsed * 1000),
                        "connector": connector,
                        "cached": resp.headers.get('X-Cache-Hit', 'false') == 'true',
                        "service": f"mac-studio-rag-{connector}"
                    }

                    # Store test result
                    test = VoiceTest(
                        test_type="rag_query",
                        test_input=query.text,
                        test_config={"connector": connector},
                        result=result,
                        success=True,
                        executed_by_id=current_user.id
                    )
                    db.add(test)
                    db.commit()

                    logger.info("rag_test_completed", connector=connector, user=current_user.username, success=True)

                    return {
                        "success": True,
                        **result
                    }
                else:
                    error_text = await resp.text()
                    raise Exception(f"HTTP {resp.status}: {error_text}")

    except Exception as e:
        logger.error("rag_test_failed", error=str(e))

        test = VoiceTest(
            test_type="rag_query",
            test_input=query.text,
            test_config={"connector": connector},
            result={},
            success=False,
            error_message=str(e),
            executed_by_id=current_user.id
        )
        db.add(test)
        db.commit()

        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipeline/test")
async def test_full_pipeline(
    query: TestQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Test full voice pipeline adapted for Mac architecture.

    Pipeline: LLM Processing → (optional RAG) → (optional HA execution) → TTS
    Note: No wake word or STT since this starts with text input
    """
    if not current_user.has_permission('write'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    if not query.text:
        raise HTTPException(status_code=400, detail="Query is required")

    try:
        timings = {}
        results = {}

        # 1. LLM Processing
        start = time.time()
        llm_url = "http://192.168.10.167:11434/api/generate"
        async with aiohttp.ClientSession() as session:
            async with session.post(llm_url, json={
                "model": "phi3:mini",
                "prompt": query.text,
                "stream": False
            }, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    timings["llm"] = time.time() - start
                    results["llm_response"] = data.get("response", "")
                else:
                    raise Exception(f"LLM failed: HTTP {resp.status}")

        # 2. TODO: RAG Enhancement (if needed)
        # 3. TODO: Home Assistant Integration (if command detected)
        # 4. TODO: TTS Generation

        total_time = sum(timings.values())

        result = {
            "timings": {k: int(v * 1000) for k, v in timings.items()},
            "total_time": int(total_time * 1000),
            "results": results,
            "target_met": total_time < 5.0,
            "note": "Simplified pipeline - only LLM stage implemented"
        }

        # Store test result
        test = VoiceTest(
            test_type="full_pipeline",
            test_input=query.text,
            test_config={"model": "phi3:mini"},
            result=result,
            success=True,
            executed_by_id=current_user.id
        )
        db.add(test)
        db.commit()

        logger.info("pipeline_test_completed", user=current_user.username, success=True,
                   total_time=total_time)

        return {
            "success": True,
            **result
        }

    except Exception as e:
        logger.error("pipeline_test_failed", error=str(e))

        test = VoiceTest(
            test_type="full_pipeline",
            test_input=query.text,
            test_config={},
            result={},
            success=False,
            error_message=str(e),
            executed_by_id=current_user.id
        )
        db.add(test)
        db.commit()

        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tests/history")
async def get_test_history(
    test_type: str = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get historical test results."""
    if not current_user.has_permission('read'):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    query = db.query(VoiceTest)

    if test_type:
        query = query.filter(VoiceTest.test_type == test_type)

    tests = query.order_by(VoiceTest.executed_at.desc()).limit(limit).all()

    return {
        "tests": [t.to_dict() for t in tests],
        "total": len(tests)
    }
