import os
import shutil
from enum import Enum

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

from core.processor import DeepgramProcessor
from core.llm import create_llm_provider
from core.config_manager import ConfigManager

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Meeting Assistant API",
    description="API for transcribing and summarizing meeting recordings",
    version="1.0.0"
)

# 1. Setup keys & Config
config = ConfigManager()
deepgram_key = config.get_deepgram_api_key()
llm_key = config.get_llm_api_key()

if not deepgram_key or not llm_key:
    # We'll log error but won't crash the import, 
    # but endpoints will fail if keys are missing
    print("[!] Warning: API keys missing in environment")

class LLMProviderName(str, Enum):
    """Supported LLM provider identifiers for per-request selection."""

    gemini = "gemini"
    deepseek = "deepseek"
    chatgpt = "chatgpt"


class SummarizationMode(str, Enum):
    """Supported summarization modes."""

    meeting = "meeting"
    english = "english"
    interview = "interview"


# Initialize components
try:
    processor = DeepgramProcessor(api_key=deepgram_key) if deepgram_key else None
    summarizer = create_llm_provider(config) if llm_key else None
except Exception as e:
    print(f"[-] Initialization Error: {e}")
    processor = None
    summarizer = None

@app.get("/health", tags=["Health"])
async def health_check():
    """Check if the service is up and running."""
    return {"status": "healthy", "keys_configured": bool(deepgram_key and llm_key)}

@app.post(
    "/process-audio",
    tags=["Processing"],
    summary="Загрузить аудиофайл и получить транскрипт + саммари",
    description=(
        "Принимает аудиофайл, отправляет его в Deepgram для транскрибации и затем генерирует саммари "
        "с использованием LLM‑провайдера по умолчанию из config.json. "
        "Если download=true, возвращает Markdown‑файл с саммари."
    ),
)
async def process_audio(
    file: UploadFile = File(...),
    download: bool = False,
):
    """
    Upload an audio file to transcribe and summarize using the default LLM provider from config.
    """
    if not processor or not summarizer:
        raise HTTPException(status_code=500, detail="API components not initialized. Check server logs for API key errors.")

    # 1. Save uploaded file to a temporary location
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, file.filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # 2. Process Audio
    try:
        print(f"[*] Starting transcription for {file.filename}...")
        transcript = processor.process_audio(file_path)

        print("[*] Starting summarization...")
        summary = summarizer.summarize(transcript)

        if download:
            safe_name = os.path.splitext(file.filename or "meeting")[0] or "meeting"
            md_bytes = summary.encode("utf-8")
            return StreamingResponse(
                iter([md_bytes]),
                media_type="text/markdown; charset=utf-8",
                headers={
                    "Content-Disposition": f'attachment; filename="{safe_name}_summary.md"'
                },
            )

        return {
            "filename": file.filename,
            "transcript": transcript,
            "summary": summary,
        }
    except Exception as e:
        print(f"[-] Processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    finally:
        # 3. Cleanup temp file
        if os.path.exists(file_path):
            os.remove(file_path)


@app.post(
    "/summarize-transcript",
    tags=["Summarization"],
    summary="Сделать саммари по загруженному тексту транскрипта",
    description=(
        "Принимает готовый текстовый файл транскрипции (UTF‑8) и генерирует саммари. "
        "Аудио не обрабатывается, только текст. LLM‑провайдер и режим саммаризации выбираются из параметров запроса. "
        "Если download=true, возвращает Markdown‑файл."
    ),
)
async def summarize_transcript(
    file: UploadFile = File(..., description="Текстовый файл транскрипции (.txt, .md и т.п.)"),
    provider: LLMProviderName = LLMProviderName.gemini,
    mode: SummarizationMode = SummarizationMode.meeting,
    download: bool = False,
):
    """
    Upload a text transcript file and generate a summary.

    Этот эндпоинт **не** выполняет транскрибацию аудио — он принимает уже готовый текст.
    Модель суммаризации можно выбрать в интерфейсе Swagger UI из выпадающего списка.
    """
    if not llm_key:
        raise HTTPException(
            status_code=500,
            detail="LLM API key is not configured. Проверьте .env и перезапустите сервер.",
        )

    try:
        summarizer = create_llm_provider(config, provider_type=provider.value)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Не удалось инициализировать LLM провайдера '{provider.value}': {e}",
        )

    try:
        raw_bytes = await file.read()
        if not raw_bytes:
            raise HTTPException(status_code=400, detail="Загруженный файл пустой.")

        try:
            transcript = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Не удалось декодировать файл как UTF-8. Убедитесь, что это текстовый файл.",
            )

        if not transcript.strip():
            raise HTTPException(status_code=400, detail="Файл не содержит текста для саммари.")

        print("[*] Starting summarization from uploaded transcript file...")
        summary = summarizer.summarize(transcript, mode=mode.value)

        if download:
            original_name = file.filename or "transcript"
            base_name = os.path.splitext(original_name)[0] or "transcript"
            safe_name = f"{base_name}_{provider.value}_{mode.value}"
            md_bytes = summary.encode("utf-8")
            return StreamingResponse(
                iter([md_bytes]),
                media_type="text/markdown; charset=utf-8",
                headers={
                    "Content-Disposition": f'attachment; filename="{safe_name}.md"'
                },
            )

        return {
            "filename": file.filename,
            "provider": provider.value,
            "mode": mode.value,
            "summary": summary,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[-] Transcript summarization failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Summarization failed: {e}",
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
