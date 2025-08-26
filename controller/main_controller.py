import json
import logging

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
import io
import PyPDF2
import httpx
app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://resmatch.netlify.app/"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/upload")
async def upload_pdf(pdf: UploadFile = File(...), description: str = Form(...), gemini_api_key: str = Form(...)):
    if pdf.content_type != "application/pdf":
        return JSONResponse(status_code=400, content={"error": "File must be a PDF."})
    print("debug", pdf.filename)
    pdf_bytes = await pdf.read()
    reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    print(text)
    prompt = (
        f"Resume:\n{text}\n\nJob Description:\n{description}\n\n"
        "1. Output a match percentage score (0-100%) based on skills and experience fit.\n"
        "2. List any missing or extra skills compared to the job description.\n"
        "3. Provide specific recommendations for improving the resume to better match the role.\n"
        "4. Output in JSON format with keys: 'match_percentage', 'missing_skills', 'recommendations'.\n"
    )
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    url = f"{GEMINI_API_URL}?key={gemini_api_key}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        resp_json = response.json()
        if "candidates" in resp_json and resp_json["candidates"]:
            llm_result = resp_json["candidates"][0]["content"]["parts"][0]["text"]
        else:
            logging.error(f"Gemini API error: {resp_json}")
            llm_result = "LLM response unavailable or error occurred."
    cleaned = llm_result.replace("json", "").replace("```", "").replace("\n", "")
    cleaned = cleaned.strip()
    print(cleaned)
    result_json = json.loads(cleaned)
    print("LLM Result:", JSONResponse(result_json))
    return JSONResponse(result_json)