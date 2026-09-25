import io
import json
import csv
import hashlib
import zipfile
from pathlib import Path

import requests
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

API_URL = "https://unpenurious-nonintrovertedly-ai.ngrok-free.dev"
BASE_DIR = Path(__file__).resolve().parent
IMAGE_DIR = BASE_DIR / "images"

IMAGE_TYPES = [
    "jpg",
    "jpeg",
    "png",
    "webp",
    "bmp",
    "tif",
    "tiff",
]


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="OMR Answer Extraction",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
<style>
.stApp {
    background-color: #f5f7fb;
}

.main-header {
    background: linear-gradient(135deg, #1e3a8a, #2563eb);
    padding: 25px 35px;
    border-radius: 15px;
    color: white;
    margin-bottom: 30px;
}

.main-header h1 {
    margin: 0;
    font-size: 32px;
}

.main-header p {
    margin-top: 8px;
    font-size: 16px;
    opacity: 0.9;
}

.section-title {
    font-size: 22px;
    font-weight: 700;
    color: #1e293b;
    margin-top: 25px;
    margin-bottom: 15px;
}

.result-card {
    background: white;
    padding: 25px;
    border-radius: 15px;
    border-left: 6px solid #2563eb;
    box-shadow: 0px 3px 15px rgba(0,0,0,0.08);
    margin-bottom: 20px;
}

.roll-number {
    font-size: 28px;
    font-weight: 700;
    color: #1d4ed8;
}

.score-card {
    background: white;
    padding: 25px;
    border-radius: 15px;
    box-shadow: 0px 3px 15px rgba(0,0,0,0.08);
    text-align: center;
    margin-top: 20px;
}

.score-number {
    font-size: 40px;
    font-weight: 800;
    color: #1d4ed8;
}

.status-correct {
    color: #15803d;
    font-weight: 700;
}

.status-wrong {
    color: #b91c1c;
    font-weight: 700;
}

.status-blank {
    color: #64748b;
    font-weight: 700;
}

/* Keep Streamlit metric text readable on the light result card. */
[data-testid="stMetricLabel"] {
    color: #334155 !important;
    font-weight: 700 !important;
}
[data-testid="stMetricValue"] {
    color: #1e3a8a !important;
    font-weight: 800 !important;
}
[data-testid="stMetricDelta"] {
    color: #475569 !important;
}
.result-summary {
    background: #ffffff;
    border-radius: 15px;
    padding: 18px 14px;
    box-shadow: 0 3px 15px rgba(0,0,0,0.08);
}

.summary-card {
    width: 100%;
    box-sizing: border-box;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 22px;
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 0;
    box-shadow: 0 4px 18px rgba(15, 23, 42, 0.08);
    margin-bottom: 24px;
}

.summary-item {
    min-width: 0;
    padding: 8px 18px;
    text-align: center;
    border-right: 1px solid #e2e8f0;
}

.summary-item:last-child {
    border-right: none;
}

.summary-label {
    color: #475569;
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 10px;
    white-space: normal;
}

.summary-value {
    color: #1e3a8a;
    font-size: 32px;
    line-height: 1.1;
    font-weight: 800;
}

.correct-value { color: #15803d; }
.wrong-value { color: #b91c1c; }
.score-value { color: #2563eb; }

@media (max-width: 900px) {
    .summary-card { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .summary-item:nth-child(3), .summary-item:nth-child(6) { border-right: none; }
}

@media (max-width: 600px) {
    .summary-card { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .summary-item { border-right: none; border-bottom: 1px solid #e2e8f0; padding: 12px 8px; }
    .summary-item:last-child, .summary-item:nth-last-child(2) { border-bottom: none; }
}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_STATE = {
    "course": None,
    "schema": None,
    "answer_key_result": None,
    "answer_key_name": None,
    "answer_key_signature": None,
    "student_result": None,
    "evaluation": None,
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


def reset_all():
    for key, value in DEFAULT_STATE.items():
        st.session_state[key] = value


# ============================================================
# HELPERS
# ============================================================

def course_label():
    if st.session_state.course == "JEE_MAINS":
        return "JEE Main"
    return "NEET"


def get_preview_path():
    """
    Looks for common preview filenames.

    Supported names:
      images/jee_schema_a.png
      images/jee_schema_b.png
      images/neet_schema_a.png
      images/neet_schema_b.png

    Also tries common JPG/JPEG/WebP variants.
    """
    prefix = (
        "jee"
        if st.session_state.course == "JEE_MAINS"
        else "neet"
    )

    schema = (
        "schema_a"
        if st.session_state.schema == "SCHEMA_A"
        else "schema_b"
    )

    candidates = [
        f"{prefix}_{schema}.png",
        f"{prefix}_{schema}.jpg",
        f"{prefix}_{schema}.jpeg",
        f"{prefix}_{schema}.webp",
        f"{prefix}_{schema}.PNG",
        f"{prefix}_{schema}.JPG",
        f"{prefix}_{schema}.JPEG",
    ]

    for name in candidates:
        path = IMAGE_DIR / name
        if path.exists():
            return path

    return None


def answer_value(value):
    if value is None:
        return None

    value = str(value).strip().upper()

    if value in {
        "",
        "NONE",
        "NULL",
        "BLANK",
        "N/A",
        "NA",
    }:
        return None

    return value


def get_answer(result, question):
    answers = result.get("answers", {})

    value = answers.get(str(question))

    if value is None:
        value = answers.get(question)

    return answer_value(value)


def evaluate(student_result, answer_key_result):
    key_answers = answer_key_result.get("answers", {})

    student_answers = student_result.get("answers", {})

    # Use the answer-key questions as the authoritative set.
    questions = sorted(
        int(q)
        for q in key_answers.keys()
        if str(q).isdigit()
    )

    rows = []

    correct = 0
    wrong = 0
    not_attempted = 0

    for question in questions:

        correct_answer = answer_value(
            key_answers.get(str(question))
        )

        if correct_answer is None:
            # A blank answer in the answer key is not a valid
            # correct-answer entry, so keep it visible rather
            # than silently treating it as a student blank.
            student_answer = answer_value(
                student_answers.get(str(question))
            )

            rows.append(
                {
                    "Question": f"Q{question}",
                    "Correct Answer": "KEY BLANK",
                    "Student Answer": (
                        student_answer
                        if student_answer is not None
                        else "Not Attempted"
                    ),
                    "Status": "Invalid Key",
                    "Marks": 0,
                }
            )
            continue

        student_answer = answer_value(
            student_answers.get(str(question))
        )

        if student_answer is None:
            status = "Not Attempted"
            marks = 0
            not_attempted += 1

        elif student_answer == "INVALID":
            status = "Wrong"
            marks = -1
            wrong += 1

        elif student_answer == correct_answer:
            status = "Correct"
            marks = 4
            correct += 1

        else:
            status = "Wrong"
            marks = -1
            wrong += 1

        rows.append(
            {
                "Question": f"Q{question}",
                "Correct Answer": correct_answer,
                "Student Answer": (
                    student_answer
                    if student_answer is not None
                    else "Not Attempted"
                ),
                "Status": status,
                "Marks": marks,
            }
        )

    total = len(questions)
    final_score = correct * 4 - wrong

    return {
        "total_questions": total,
        "correct": correct,
        "wrong": wrong,
        "not_attempted": not_attempted,
        "final_score": final_score,
        "rows": rows,
    }


def process_image(uploaded_file, endpoint):
    uploaded_file.seek(0)

    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            uploaded_file.type or "application/octet-stream",
        )
    }

    data = {
        "exam": st.session_state.course,
        "schema": st.session_state.schema,
    }

    response = requests.post(
        f"{API_URL}{endpoint}",
        files=files,
        data=data,
        timeout=120,
    )

    if response.status_code != 200:
        try:
            detail = response.json().get(
                "detail",
                "Unknown backend error",
            )
        except Exception:
            detail = response.text

        raise RuntimeError(detail)

    return response.json()


def create_download_json():
    result = st.session_state.student_result
    evaluation = st.session_state.evaluation

    roll_number = result.get(
        "roll_number",
        "Not Detected",
    )

    return {
        "candidate_rollno": roll_number,
        "course": course_label(),
        "schema": st.session_state.schema,
        "answer_key_file": st.session_state.answer_key_name,
        "total_questions": evaluation["total_questions"],
        "correct": evaluation["correct"],
        "wrong": evaluation["wrong"],
        "not_attempted": evaluation["not_attempted"],
        "correct_marks": evaluation["correct"] * 4,
        "negative_marks": evaluation["wrong"],
        "final_score": evaluation["final_score"],
        "question_wise_results": evaluation["rows"],
    }


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
<div class="main-header">
    <h1>📝 OMR Answer Extraction System</h1>
    <p>OMR Answer Extraction & Evaluation</p>
</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# 1. COURSE
# ============================================================

st.markdown(
    '<div class="section-title">1. Select Course</div>',
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2)

with col1:
    if st.button(
        "🎓 JEE MAINS",
        use_container_width=True,
        type="primary",
    ):
        reset_all()
        st.session_state.course = "JEE_MAINS"
        st.rerun()

with col2:
    if st.button(
        "🩺 NEET",
        use_container_width=True,
        type="primary",
    ):
        reset_all()
        st.session_state.course = "NEET"
        st.rerun()


if st.session_state.course:

    st.success(
        f"Selected Course: **{course_label()}**"
    )


# ============================================================
# 2. SCHEMA
# ============================================================

if st.session_state.course:

    st.markdown(
        '<div class="section-title">2. Select OMR Schema</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "📄 SCHEMA A",
            use_container_width=True,
        ):
            st.session_state.schema = "SCHEMA_A"
            st.session_state.answer_key_result = None
            st.session_state.answer_key_name = None
            st.session_state.student_result = None
            st.session_state.evaluation = None
            st.rerun()

    with col2:
        if st.button(
            "📄 SCHEMA B",
            use_container_width=True,
        ):
            st.session_state.schema = "SCHEMA_B"
            st.session_state.answer_key_result = None
            st.session_state.answer_key_name = None
            st.session_state.student_result = None
            st.session_state.evaluation = None
            st.rerun()


# ============================================================
# 3. PREVIEW
# ============================================================

if st.session_state.schema:

    st.markdown(
        '<div class="section-title">3. OMR Preview</div>',
        unsafe_allow_html=True,
    )

    preview_path = get_preview_path()

    if preview_path:

        st.info(
            f"Preview: **{course_label()} - "
            f"{st.session_state.schema}**"
        )

        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            st.image(
                str(preview_path),
                caption=(
                    f"{course_label()} - "
                    f"{st.session_state.schema}"
                ),
                use_container_width=True,
            )

    else:

        st.warning(
            "Preview image was not found."
        )

        st.caption(
            "Expected one of these filenames: "
            f"{course_label().lower().replace(' ', '_')}_"
            f"{st.session_state.schema.lower()}.png "
            "inside the images folder."
        )


# ============================================================
# 4. ANSWER KEY IMAGE
# ============================================================

if st.session_state.schema:

    st.markdown(
        '<div class="section-title">4. Upload Answer Key OMR</div>',
        unsafe_allow_html=True,
    )

    st.info(
        "Upload the completed answer-key OMR image. "
        "It is processed automatically using the selected course and schema. "
        "The uploaded image and extracted key are kept hidden."
    )

    answer_key_file = st.file_uploader(
        "Upload Answer-Key OMR Image",
        type=IMAGE_TYPES,
        key="answer_key_file",
    )

    if answer_key_file:

        answer_key_bytes = answer_key_file.getvalue()
        answer_key_signature = hashlib.sha256(
            answer_key_bytes
        ).hexdigest()

        # Extract automatically once for this exact uploaded image.
        if (
            st.session_state.answer_key_result is None
            or st.session_state.answer_key_signature
            != answer_key_signature
        ):

            with st.spinner(
                "Processing answer key..."
            ):

                try:

                    answer_key_result = process_image(
                        answer_key_file,
                        "/api/omr/process-answer-key",
                    )

                    st.session_state.answer_key_result = (
                        answer_key_result
                    )

                    st.session_state.answer_key_name = (
                        answer_key_file.name
                    )

                    st.session_state.answer_key_signature = (
                        answer_key_signature
                    )

                    # A new key must clear any previous student result.
                    st.session_state.student_result = None
                    st.session_state.evaluation = None

                except requests.exceptions.ConnectionError:
                    st.error(
                        "Cannot connect to FastAPI. "
                        "Start the backend on port 8000."
                    )

                except requests.exceptions.Timeout:
                    st.error(
                        "Answer-key processing timed out."
                    )

                except Exception as exc:
                    st.error(
                        f"Answer-key processing failed: {exc}"
                    )

        if st.session_state.answer_key_result:
            st.success(
                "Answer key uploaded and processed successfully. "
                "You can now upload the student OMR."
            )


# ============================================================
# 5. STUDENT OMR
# ============================================================

if (
    st.session_state.schema
    and st.session_state.answer_key_result
):

    st.markdown(
        '<div class="section-title">5. Upload Student OMR</div>',
        unsafe_allow_html=True,
    )

    st.info(
        "Upload the student OMR image and click Analyze OMR. "
        "The uploaded image is processed but is not displayed below."
    )

    uploaded_file = st.file_uploader(
        "Upload Student OMR Sheet",
        type=IMAGE_TYPES,
        key="student_omr_file",
    )

    if uploaded_file:

        if st.button(
            "🔍 ANALYZE OMR",
            use_container_width=True,
            type="primary",
        ):

            with st.spinner(
                "Extracting and matching answers..."
            ):

                try:

                    student_result = process_image(
                        uploaded_file,
                        "/api/omr/process",
                    )

                    evaluation = evaluate(
                        student_result,
                        st.session_state.answer_key_result,
                    )

                    st.session_state.student_result = (
                        student_result
                    )

                    st.session_state.evaluation = (
                        evaluation
                    )

                    st.success(
                        "OMR analyzed and matched with the answer key. "
                        "Open the Result tab below."
                    )

                except requests.exceptions.ConnectionError:
                    st.error(
                        "Cannot connect to FastAPI. "
                        "Start the backend on port 8000."
                    )

                except requests.exceptions.Timeout:
                    st.error(
                        "OMR processing timed out."
                    )

                except Exception as exc:
                    st.error(
                        f"OMR analysis failed: {exc}"
                    )


# ============================================================
# 6. RESULT TAB
# ============================================================

if (
    st.session_state.student_result
    and st.session_state.evaluation
):

    result_tab, download_tab = st.tabs(
        ["📊 Result", "⬇️ Download Result"]
    )

    with result_tab:

        result = st.session_state.student_result
        evaluation = st.session_state.evaluation

        st.markdown(
            '<div class="section-title">6. Final Result</div>',
            unsafe_allow_html=True,
        )

        roll_number = result.get(
            "roll_number",
            "Not Detected",
        )

        # Candidate details are shown first in the result tab.
        st.markdown(
            f"""
            <div class="result-card">
                <div class="roll-number">
                    Candidate Rollno : {roll_number}
                </div>
                <div style="margin-top:12px;color:#475569;font-size:15px;">
                    <b>Course:</b> {course_label()}
                    &nbsp;&nbsp;&nbsp;&nbsp;
                    <b>Schema:</b> {st.session_state.schema}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Render the complete summary as one HTML card so every value stays
        # inside the same visible box. Question-wise comparison is only
        # available in the downloadable report.
        st.markdown("### 📊 Result Summary")

        total_questions = evaluation["total_questions"]
        attempted = evaluation["correct"] + evaluation["wrong"]
        correct = evaluation["correct"]
        wrong = evaluation["wrong"]
        not_attempted = evaluation["not_attempted"]
        final_score = evaluation["final_score"]

        st.markdown(
            f"""
            <div class="summary-card">
                <div class="summary-item">
                    <div class="summary-label">Total Questions</div>
                    <div class="summary-value">{total_questions}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Attempted Questions</div>
                    <div class="summary-value">{attempted}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Correct</div>
                    <div class="summary-value correct-value">{correct}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Wrong</div>
                    <div class="summary-value wrong-value">{wrong}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Not Attempted</div>
                    <div class="summary-value">{not_attempted}</div>
                </div>
                <div class="summary-item score-item">
                    <div class="summary-label">Total Score</div>
                    <div class="summary-value score-value">{final_score}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.info(
            "Question-wise answer comparison is included in the downloadable report. "
            "It is not displayed on this screen."
        )

    with download_tab:

        result = st.session_state.student_result
        evaluation = st.session_state.evaluation

        roll_number = result.get(
            "roll_number",
            "Not Detected",
        )

        st.markdown("### ⬇️ Download Result")

        download_result = create_download_json()

        json_data = json.dumps(
            download_result,
            indent=4,
            ensure_ascii=False,
        )

        safe_roll = str(
            roll_number
        ).replace(" ", "_")

        json_filename = (
            f"{safe_roll}_"
            f"{st.session_state.course}_"
            f"{st.session_state.schema}_"
            f"result.json"
        )

        st.download_button(
            "⬇️ Download Complete Result",
            data=json_data,
            file_name=json_filename,
            mime="application/json",
            use_container_width=True,
        )

        csv_buffer = io.StringIO()

        writer = csv.DictWriter(
            csv_buffer,
            fieldnames=[
                "Question",
                "Correct Answer",
                "Student Answer",
                "Status",
                "Marks",
            ],
        )

        writer.writeheader()
        writer.writerows(
            evaluation["rows"]
        )

        csv_buffer.write("\n")
        csv_buffer.write(
            f"Candidate Rollno,{roll_number}\n"
        )
        csv_buffer.write(
            f"Total Questions,{evaluation['total_questions']}\n"
        )
        csv_buffer.write(
            f"Correct,{evaluation['correct']}\n"
        )
        csv_buffer.write(
            f"Wrong,{evaluation['wrong']}\n"
        )
        csv_buffer.write(
            f"Not Attempted,{evaluation['not_attempted']}\n"
        )
        csv_buffer.write(
            f"Final Score,{evaluation['final_score']}\n"
        )

        csv_filename = (
            f"{safe_roll}_"
            f"{st.session_state.course}_"
            f"{st.session_state.schema}_"
            f"result.csv"
        )

        st.download_button(
            "⬇️ Download CSV Result",
            data=csv_buffer.getvalue(),
            file_name=csv_filename,
            mime="text/csv",
            use_container_width=True,
        )

    st.markdown("---")

    if st.button(
        "🔄 Process Another OMR",
        use_container_width=True,
    ):
        reset_all()
        st.rerun()
