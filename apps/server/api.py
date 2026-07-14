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


class GeminiRegionBlockedError(RuntimeError):
    """Raised when Gemini is unavailable in the current user region."""


def _ascii_safe_header_value(value: str, max_len: int = 500) -> str:
    """Convert arbitrary text to a latin-1 safe HTTP header value."""
    return value.encode("ascii", "replace").decode("ascii")[:max_len]


def _summarize_with_provider_fallback(transcript: str, meeting_mode: str = "meeting") -> str:
    """
    Summarize transcript with default provider, then fallback if Gemini is region-blocked.
    """
    default_provider = config.get_llm_provider_type()
    primary_summarizer = create_llm_provider(config, provider_type=default_provider)

    try:
        return primary_summarizer.summarize(transcript, mode=meeting_mode)
    except Exception as e:
        error_msg = str(e).lower()
        gemini_region_blocked = (
            default_provider == "gemini"
            and (
                "user location is not supported" in error_msg
                or "location is not supported" in error_msg
            )
            and ("failed_precondition" in error_msg or "400" in error_msg)
        )
        if not gemini_region_blocked:
            raise

        print("[!] Gemini region restriction detected. Trying fallback providers...")
        fallback_errors = []
        tried_provider = False
        for provider_name in ("deepseek", "chatgpt"):
            api_key = config.get_llm_api_key(provider_name)
            if not api_key:
                continue
            tried_provider = True
            try:
                fallback_summarizer = create_llm_provider(config, provider_type=provider_name)
                return fallback_summarizer.summarize(transcript, mode=meeting_mode)
            except Exception as fallback_error:
                fallback_errors.append(f"{provider_name}: {fallback_error}")
                print(f"[!] Fallback provider '{provider_name}' failed: {fallback_error}")

        if not tried_provider:
            raise GeminiRegionBlockedError(
                "Gemini недоступен в вашем регионе. Добавьте `DEEPSEEK_API_KEY` или "
                "`OPENAI_API_KEY` в `.env`, либо смените `llm.provider` в `config.json`."
            ) from e

        raise GeminiRegionBlockedError(
            "Gemini недоступен в вашем регионе, а fallback-провайдеры тоже завершились ошибкой: "
            + "; ".join(fallback_errors)
        ) from e


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
        "Тип саммаризации можно выбрать через параметр mode (meeting/english/interview). "
        "Если download=true, возвращает Markdown‑файл с саммари."
    ),
)
async def process_audio(
    file: UploadFile = File(...),
    download: bool = False,
    mode: SummarizationMode = SummarizationMode.meeting,
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
    except Exception as e:
        print(f"[-] Transcription failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    summary = None
    summary_error = None
    try:
        print("[*] Starting summarization...")
        summary = _summarize_with_provider_fallback(transcript, meeting_mode=mode.value)
    except Exception as e:
        summary_error = str(e)
        print(f"[!] Summarization failed, returning transcript only: {summary_error}")

    try:
        if download:
            safe_name = os.path.splitext(file.filename or "meeting")[0] or "meeting"
            if summary:
                md_bytes = summary.encode("utf-8")
                download_filename = f"{safe_name}_summary.md"
            else:
                transcript_md = (
                    f"# Transcript\n\n"
                    f"**Source file:** {file.filename}\n\n"
                    f"---\n\n"
                    f"{transcript}"
                )
                md_bytes = transcript_md.encode("utf-8")
                download_filename = f"{safe_name}_transcript.md"

            headers = {"Content-Disposition": f'attachment; filename="{download_filename}"'}
            if summary_error:
                headers["X-Summary-Error"] = _ascii_safe_header_value(summary_error)

            return StreamingResponse(
                iter([md_bytes]),
                media_type="text/markdown; charset=utf-8",
                headers=headers,
            )

        return {
            "filename": file.filename,
            "mode": mode.value,
            "transcript": transcript,
            "summary": summary,
            "summary_error": summary_error,
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
