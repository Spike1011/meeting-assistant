import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from core.processor import DeepgramProcessor
from core.summarizer import LLMSummarizer

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Meeting Assistant API",
    description="API for transcribing and summarizing meeting recordings",
    version="1.0.0"
)

# 1. Setup keys
deepgram_key = os.getenv("DEEPGRAM_API_KEY")
llm_key = os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY")

if not deepgram_key or not llm_key:
    # We'll log error but won't crash the import, 
    # but endpoints will fail if keys are missing
    print("Warning: API keys missing in environment")

# Initialize components
try:
    processor = DeepgramProcessor(api_key=deepgram_key) if deepgram_key else None
    summarizer = LLMSummarizer(api_key=llm_key) if llm_key else None
except Exception as e:
    print(f"Initialization Error: {e}")
    processor = None
    summarizer = None

@app.get("/health", tags=["Health"])
async def health_check():
    """Check if the service is up and running."""
    return {"status": "healthy", "keys_configured": bool(deepgram_key and llm_key)}

@app.post("/process-audio", tags=["Processing"])
async def process_audio(file: UploadFile = File(...)):
    """
    Upload an audio file to transcribe and summarize.
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
        print(f"Starting transcription for {file.filename}...")
        transcript = processor.process_audio(file_path)
        
        print("Starting summarization...")
        summary = summarizer.summarize(transcript)
        
        return {
            "filename": file.filename,
            "transcript": transcript,
            "summary": summary
        }
    except Exception as e:
        print(f"Processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    finally:
        # 3. Cleanup temp file
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
