from pathlib import Path
from contextlib import redirect_stdout
import io

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.omr_reader import process_jee_main, process_neet, resize_to_template
from app.schemas import JEE_MAIN_SCHEMAS, NEET_SCHEMAS

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(
    title="OMR Processing API",
    description="OMR answer extraction for JEE Main and NEET templates.",
    version="1.0.0",
)

# Change allow_origins to your production frontend URL(s) before deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

EXAMS = {
    "JEE_MAINS": {
        "label": "JEE Main",
        "schemas": JEE_MAIN_SCHEMAS,
    },
    "NEET": {
        "label": "NEET",
        "schemas": NEET_SCHEMAS,
    },
}


def normalize_exam(value: str) -> str:
    value = value.strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "JEE_MAIN": "JEE_MAINS",
        "JEE_MAINS": "JEE_MAINS",
        "NEET": "NEET",
    }
    return aliases.get(value, value)


def normalize_schema(value: str) -> str:
    value = value.strip().upper()
    if value.startswith("SCHEMA_"):
        value = value[-1:]
    return value


def build_response(result, exam_name: str, roll_number, schema_variant: str):
    answered = sum(
        answer not in (None, "INVALID")
        for answer in result.values()
    )
    blank = sum(answer is None for answer in result.values())
    invalid = sum(answer == "INVALID" for answer in result.values())

    # These are the same fields produced by the existing save_json() flow,
    # with schema_variant added so the frontend knows which template was used.
    return {
        "exam": exam_name,
        "schema": f"SCHEMA_{schema_variant}",
        "total_questions": len(result),
        "answered": answered,
        "blank": blank,
        "invalid": invalid,
        "roll_number": roll_number,
        "answers": result,
    }


@app.get("/")
def root():
    return {
        "message": "OMR Processing API is running",
        "docs": "/docs",
        "endpoint": "POST /api/omr/process",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/omr/options")
def get_omr_options():
    return {
        "exams": [
            {
                "value": exam_key,
                "label": exam_data["label"],
                "schemas": [f"SCHEMA_{variant}" for variant in exam_data["schemas"]],
            }
            for exam_key, exam_data in EXAMS.items()
        ]
    }


@app.post("/api/omr/process")
async def process_omr(
    exam: str = Form(...),
    schema: str = Form(...),
    file: UploadFile = File(...),
):
    exam_key = normalize_exam(exam)
    schema_variant = normalize_schema(schema)

    if exam_key not in EXAMS:
        raise HTTPException(
            status_code=400,
            detail="Invalid exam. Use JEE_MAINS or NEET.",
        )

    if schema_variant not in EXAMS[exam_key]["schemas"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid schema. Use SCHEMA_A or SCHEMA_B.",
        )

    if not file.filename:
        raise HTTPException(status_code=400, detail="No image file supplied.")

    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
    extension = Path(file.filename).suffix.lower()
    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type: {extension or 'unknown'}",
        )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded image is empty.")

    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image is None:
        raise HTTPException(
            status_code=400,
            detail="OpenCV could not decode the uploaded image.",
        )

    selected_schema = EXAMS[exam_key]["schemas"][schema_variant]
    image = resize_to_template(image, selected_schema)

    try:
        # The original OMR functions print detailed detection logs for the
        # CLI. Keep those logs out of the API response/server console.
        with redirect_stdout(io.StringIO()):
            if exam_key == "JEE_MAINS":
                result, _debug, roll_number = process_jee_main(
                    image,
                    selected_schema,
                )
            else:
                result, _debug, roll_number = process_neet(
                    image,
                    selected_schema,
                )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        # Keep internal details out of the production response.
        raise HTTPException(
            status_code=500,
            detail="OMR processing failed.",
        ) from exc

    return build_response(
        result,
        selected_schema["name"],
        roll_number,
        schema_variant,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
