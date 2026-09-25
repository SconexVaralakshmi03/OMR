from pathlib import Path
from contextlib import redirect_stdout
import io

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.omr_reader import process_jee_main, process_neet, resize_to_template
from app.schemas import JEE_MAIN_SCHEMAS, NEET_SCHEMAS


app = FastAPI(
    title="OMR Processing API",
    description="OMR answer extraction for JEE Main and NEET templates.",
    version="1.1.0",
)

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

ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp",
    ".bmp", ".tif", ".tiff"
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


def validate_selection(exam: str, schema: str):
    exam_key = normalize_exam(exam)
    schema_variant = normalize_schema(schema)

    if exam_key not in EXAMS:
        raise HTTPException(
            status_code=400,
            detail="Invalid exam. Use JEE_MAINS or NEET."
        )

    if schema_variant not in EXAMS[exam_key]["schemas"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid schema. Use SCHEMA_A or SCHEMA_B."
        )

    return exam_key, schema_variant, EXAMS[exam_key]["schemas"][schema_variant]


async def read_uploaded_image(file: UploadFile):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No image file supplied."
        )

    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type: {extension or 'unknown'}"
        )

    image_bytes = await file.read()

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded image is empty."
        )

    image_array = np.frombuffer(
        image_bytes,
        dtype=np.uint8
    )

    image = cv2.imdecode(
        image_array,
        cv2.IMREAD_COLOR
    )

    if image is None:
        raise HTTPException(
            status_code=400,
            detail="OpenCV could not decode the uploaded image."
        )

    return image


def extract_answers(image, exam_key, selected_schema):
    image = resize_to_template(
        image,
        selected_schema
    )

    try:
        # Keep CLI/debug print statements out of the API console.
        with redirect_stdout(io.StringIO()):

            if exam_key == "JEE_MAINS":
                result, debug, roll_number = process_jee_main(
                    image,
                    selected_schema
                )
            else:
                result, debug, roll_number = process_neet(
                    image,
                    selected_schema
                )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc)
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="OMR processing failed."
        ) from exc

    return result, debug, roll_number


def build_response(
    result,
    exam_name,
    roll_number,
    schema_variant,
    answer_key=False
):
    answered = sum(
        answer not in (None, "INVALID")
        for answer in result.values()
    )

    blank = sum(
        answer is None
        for answer in result.values()
    )

    invalid = sum(
        answer == "INVALID"
        for answer in result.values()
    )

    response = {
        "exam": exam_name,
        "schema": f"SCHEMA_{schema_variant}",
        "total_questions": len(result),
        "answered": answered,
        "blank": blank,
        "invalid": invalid,
        "roll_number": None if answer_key else roll_number,
        "answers": result,
        "is_answer_key": answer_key,
    }

    return response


@app.get("/")
def root():
    return {
        "message": "OMR Processing API is running",
        "docs": "/docs",
        "student_endpoint": "POST /api/omr/process",
        "answer_key_endpoint": "POST /api/omr/process-answer-key",
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
                "schemas": [
                    f"SCHEMA_{variant}"
                    for variant in exam_data["schemas"]
                ],
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
    exam_key, schema_variant, selected_schema = validate_selection(
        exam,
        schema
    )

    image = await read_uploaded_image(file)

    result, _debug, roll_number = extract_answers(
        image,
        exam_key,
        selected_schema
    )

    return build_response(
        result,
        selected_schema["name"],
        roll_number,
        schema_variant,
        answer_key=False
    )


@app.post("/api/omr/process-answer-key")
async def process_answer_key(
    exam: str = Form(...),
    schema: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Extract the correct answers from an answer-key OMR image.

    The selected exam/schema is used for the exact same geometry
    as the student's OMR. Roll number is deliberately ignored.
    """
    exam_key, schema_variant, selected_schema = validate_selection(
        exam,
        schema
    )

    image = await read_uploaded_image(file)

    result, _debug, _roll_number = extract_answers(
        image,
        exam_key,
        selected_schema
    )

    return build_response(
        result,
        selected_schema["name"],
        None,
        schema_variant,
        answer_key=True
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
