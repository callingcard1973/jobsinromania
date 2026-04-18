"""CV Parser API — FastAPI routes."""
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from parser import text_from_file, extract_linkedin, llm_parse

app = FastAPI(title="CV Parser API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)


class URLRequest(BaseModel):
    url: str


@app.post("/parse-cv")
async def parse_cv(
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = None,
):
    """Accept multipart file upload OR JSON {url} and return structured CV JSON."""
    try:
        if file and file.filename:
            file_bytes = await file.read()
            if not file_bytes:
                raise HTTPException(400, "Empty file")
            raw_text = text_from_file(file.filename, file_bytes)
        elif url:
            raw_text = extract_linkedin(url)
        else:
            raise HTTPException(400, "Provide a file or a url")

        if not raw_text or len(raw_text.strip()) < 30:
            raise HTTPException(422, "Could not extract readable text from input")

        cv_data = llm_parse(raw_text)
        return {"status": "ok", "cv": cv_data}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(500, f"Internal error: {e}")


@app.post("/parse-cv-url")
async def parse_cv_url(body: URLRequest):
    """JSON endpoint: {"url": "https://linkedin.com/in/..."} """
    try:
        raw_text = extract_linkedin(body.url)
        if not raw_text or len(raw_text.strip()) < 30:
            raise HTTPException(422, "Could not extract text from URL")
        cv_data = llm_parse(raw_text)
        return {"status": "ok", "cv": cv_data}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(500, f"Internal error: {e}")


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=5050, reload=False)
