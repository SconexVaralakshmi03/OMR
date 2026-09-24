# OMR FastAPI Backend

FastAPI wrapper around the existing OMR extraction logic.

## Supported combinations

- `JEE_MAINS` + `SCHEMA_A`
- `JEE_MAINS` + `SCHEMA_B`
- `NEET` + `SCHEMA_A`
- `NEET` + `SCHEMA_B`

The API keeps the existing schema coordinates and OMR detection logic. The frontend only needs to send the selected exam, selected schema, and OMR image.

## 1. Install

Create a Python 3.10+ virtual environment and install dependencies:

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Linux/macOS:

```bash
source venv/bin/activate
```

Then:

```bash
pip install -r requirements.txt
```

## 2. Start API

```bash
python main.py
```

API:

```text
http://localhost:8000
```

Swagger UI:

```text
http://localhost:8000/docs
```

## 3. Frontend request

Use `multipart/form-data`.

Fields:

```text
exam   = JEE_MAINS
schema = SCHEMA_A
file   = <OMR image>
```

Example JavaScript:

```javascript
const formData = new FormData();
formData.append("exam", "JEE_MAINS");
formData.append("schema", "SCHEMA_A");
formData.append("file", selectedFile);

const response = await fetch("http://localhost:8000/api/omr/process", {
  method: "POST",
  body: formData,
});

const data = await response.json();
console.log(data);
```

Do not manually set the `Content-Type` header when using `FormData`; the browser adds the multipart boundary automatically.

## 4. Response

Example:

```json
{
  "exam": "JEE Main",
  "schema": "SCHEMA_A",
  "total_questions": 75,
  "answered": 70,
  "blank": 4,
  "invalid": 1,
  "roll_number": "1234567",
  "answers": {
    "1": "A",
    "2": "C",
    "3": null
  }
}
```

JEE Main Schema A currently extracts 75 questions (25 Physics + 25 Chemistry + 25 Mathematics).

JEE Main Schema B extracts 90 questions.

NEET Schema A extracts 200 questions.

NEET Schema B extracts 180 questions according to the physical rows represented by the supplied Schema B template.

## 5. Get frontend dropdown options

```http
GET /api/omr/options
```

Returns:

```json
{
  "exams": [
    {
      "value": "JEE_MAINS",
      "label": "JEE Main",
      "schemas": ["SCHEMA_A", "SCHEMA_B"]
    },
    {
      "value": "NEET",
      "label": "NEET",
      "schemas": ["SCHEMA_A", "SCHEMA_B"]
    }
  ]
}
```

## Notes

- The uploaded image is resized to the selected schema's template dimensions before bubble detection, matching the existing CLI behavior.
- No OMR image is permanently stored by the API.
- The API does not write the JSON result to disk; it returns the result directly to the frontend.
- CORS is currently open for development. Restrict `allow_origins` to your frontend URL before production deployment.
