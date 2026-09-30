# omr_reader.py

import cv2
import numpy as np
import json
import os

from app.schemas import (
    SCHEMAS,
    JEE_MAIN_SCHEMAS,
    JEE_ADVANCED_SCHEMAS,
    NEET_SCHEMAS,
)


# ============================================================
# Detection settings
# ============================================================

BLACK_CHANNEL_MAX = 120
BUBBLE_RADIUS = 5

# These are intentionally conservative because the template
# contains many magenta printed circles.
FILLED_THRESHOLD = 0.20
MULTIPLE_MARK_THRESHOLD = 0.20


# ============================================================
# Select exam
# ============================================================

def select_omr_type():
    print("\n" + "=" * 60)
    print("             OMR ANSWER EXTRACTION")
    print("=" * 60)
    print("\nSelect OMR type:")
    print("1. JEE Main")
    print("2. NEET")
    print("3. JEE Advanced")

    while True:
        choice = input("\nEnter option (1/2/3): ").strip()

        if choice in SCHEMAS:
            return choice

        print("Invalid choice. Enter 1, 2 or 3.")


# ============================================================
# Select JEE Main schema
# ============================================================

def select_jee_main_schema():
    print("\n" + "=" * 60)
    print("             JEE MAIN SCHEMA")
    print("=" * 60)
    print("\nSelect JEE Main OMR schema:")
    print("A. Existing JEE Main format")
    print("B. New JEE Main format")
    print("C. JEE Main format with numerical grids")
    print("D. JEE Main format, 75 questions (blue ink, split numeric)")

    while True:
        variant = input("\nEnter schema (A/B/C/D): ").strip().upper()

        if variant in JEE_MAIN_SCHEMAS:
            return variant

        print("Invalid choice. Enter A, B, C or D.")


# ============================================================
# Select JEE Advanced schema
# ============================================================

def select_jee_advanced_schema():
    print("\n" + "=" * 60)
    print("             JEE ADVANCED SCHEMA")
    print("=" * 60)
    print("\nSelect JEE Advanced OMR schema:")
    print("A. JEE Advanced format, 54 questions (MCQ, numerical, paragraph)")

    while True:
        variant = input("\nEnter schema (A): ").strip().upper()

        if variant in JEE_ADVANCED_SCHEMAS:
            return variant

        print("Invalid choice. Enter A.")


# ============================================================
# Select NEET schema
# ============================================================

def select_neet_schema():
    print("\n" + "=" * 60)
    print("             NEET SCHEMA")
    print("=" * 60)
    print("\nSelect NEET OMR schema:")
    print("A. Existing NEET format")
    print("B. New NEET format")
    print("C. NEET format with 50-row blocks (Q1-Q200)")

    while True:
        variant = input("\nEnter schema (A/B/C): ").strip().upper()

        if variant in NEET_SCHEMAS:
            return variant

        print("Invalid choice. Enter A, B or C.")



# ============================================================
# Get image path
# ============================================================

def get_image_path():
    path = input("\nEnter OMR image path: ").strip().strip('"')

    if not os.path.isfile(path):
        raise FileNotFoundError(f"Image not found: {path}")

    return path


# ============================================================
# Resize to template
# ============================================================

def resize_to_template(image, schema):
    return cv2.resize(
        image,
        (
            schema["template_width"],
            schema["template_height"]
        ),
        interpolation=cv2.INTER_AREA
    )


# ============================================================
# Black ink ratio
# ============================================================

def bubble_black_ratio(image, x, y, radius=BUBBLE_RADIUS):
    h, w = image.shape[:2]

    cx = int(round(x))
    cy = int(round(y))

    x1 = max(0, cx - radius)
    x2 = min(w, cx + radius + 1)
    y1 = max(0, cy - radius)
    y2 = min(h, cy + radius + 1)

    roi = image[y1:y2, x1:x2]

    if roi.size == 0:
        return 0.0

    rh, rw = roi.shape[:2]
    yy, xx = np.ogrid[:rh, :rw]

    center_x = cx - x1
    center_y = cy - y1

    circular_mask = (
        (xx - center_x) ** 2 +
        (yy - center_y) ** 2
    ) <= radius ** 2

    pixels = roi[circular_mask]

    # OpenCV is BGR. Requiring ALL channels to be dark prevents
    # the magenta printed template from looking like black ink.
    black_pixels = np.all(
        pixels < BLACK_CHANNEL_MAX,
        axis=1
    )

    return float(np.mean(black_pixels))


# ============================================================
# Read A/B/C/D response
# ============================================================

def read_choice_question(
    image,
    x_positions,
    y,
    options,
    allow_multiple=False
):
    scores = [
        bubble_black_ratio(image, x, y)
        for x in x_positions
    ]

    marked = [
        i for i, score in enumerate(scores)
        if score >= MULTIPLE_MARK_THRESHOLD
    ]

    if not marked:
        return None, scores

    if allow_multiple:
        return (
            [options[i] for i in marked],
            scores
        )

    if len(marked) > 1:
        return "INVALID", scores

    return options[marked[0]], scores


# ============================================================
# Read one numerical digit
# ============================================================

def read_digit_question(
    image,
    x,
    digit_y_positions
):
    scores = [
        bubble_black_ratio(image, x, y)
        for y in digit_y_positions
    ]

    marked = [
        digit
        for digit, score in enumerate(scores)
        if score >= MULTIPLE_MARK_THRESHOLD
    ]

    if not marked:
        return None, scores

    if len(marked) > 1:
        return "INVALID", scores

    return str(marked[0]), scores



# ============================================================
# JEE MAIN ROLL NUMBER
# ============================================================

def read_roll_number(image, roll_schema):
    """
    Read the roll number from the 0-9 bubble grid.

    The same function is used for JEE Main and NEET.
    The number of columns comes from the selected schema.
    Each roll-number column is checked independently.
    """
    digits = []

    for x in roll_schema["x_positions"]:
        scores = [
            bubble_black_ratio(image, x, y)
            for y in roll_schema["digit_y_positions"]
        ]

        marked = [
            digit
            for digit, score in enumerate(scores)
            if score >= MULTIPLE_MARK_THRESHOLD
        ]

        if not marked:
            digits.append(None)
        elif len(marked) > 1:
            digits.append("INVALID")
        else:
            digits.append(str(marked[0]))

    if any(d in (None, "INVALID") for d in digits):
        return None, digits

    return "".join(digits), digits


# ============================================================
# JEE MAIN
# ============================================================

def process_jee_main(image, schema):
    # Schema D: split MCQ blocks + 4-digit numerical answers.
    if schema.get("layout") == "mcq_split_numeric":
        return process_jee_main_schema_d(image, schema)

    # Schema C uses a different mixed MCQ/numerical layout.
    if "numeric_questions" in schema:
        return process_jee_main_schema_c(image, schema)

    debug = image.copy()
    result = {}

    options = schema["options"]

    # --------------------------------------------------------
    # Read Roll Number separately.
    # This does NOT modify the question-answer structure.
    # --------------------------------------------------------
    roll_number, roll_debug = read_roll_number(
        image,
        schema["roll_number"]
    )

    print("\n" + "=" * 40)
    print("ROLL NUMBER")
    print("=" * 40)
    print(f"Roll Number: {roll_number}")
    print(f"Roll Number columns: {roll_debug}")

    # --------------------------------------------------------
    # Existing JEE Main question extraction
    # --------------------------------------------------------
    for subject_name, subject in schema["subjects"].items():
        print("\n" + "=" * 40)
        print(subject_name)
        print("=" * 40)

        start_question = subject["start_question"]

        for row, y in enumerate(subject["y_positions"]):
            question_number = start_question + row

            answer, scores = read_choice_question(
                image,
                subject["x_positions"],
                y,
                options
            )

            result[str(question_number)] = answer

            print(
                f"Q{question_number:03d}: {answer} "
                f"scores={[round(s, 3) for s in scores]}"
            )

            if answer in options:
                index = options.index(answer)
                cv2.circle(
                    debug,
                    (
                        subject["x_positions"][index],
                        y
                    ),
                    10,
                    (255, 0, 0),
                    2
                )

    return result, debug, roll_number



# ============================================================
# JEE MAIN SCHEMA C - NUMERICAL RESPONSE GRID
# ============================================================

def read_schema_c_numeric_question(
    image,
    x_positions,
    y_positions,
):
    """
    Schema C numerical grid.

    Each of the 7 physical columns can contain one of:
      '-'  (minus)
      '.'  (decimal point)
      0-9  (digit)

    Blank columns are ignored when the extracted answer string is
    assembled. A high threshold is used because the last response
    row is close to the magenta separator line in this template.
    """
    numeric_options = ["-", "."] + list("0123456789")
    selected = []

    for x in x_positions:
        scores = [
            bubble_black_ratio(
                image,
                x,
                y,
                radius=5
            )
            for y in y_positions
        ]

        marked = [
            i
            for i, score in enumerate(scores)
            if score >= 0.65
        ]

        if len(marked) > 1:
            selected.append("INVALID")
        elif len(marked) == 1:
            selected.append(numeric_options[marked[0]])
        else:
            selected.append("")

    if all(value == "" for value in selected):
        return None, selected

    if "INVALID" in selected:
        return "INVALID", selected

    # Preserve the physical left-to-right order while removing
    # unused blank columns.
    return "".join(
        value
        for value in selected
        if value != ""
    ), selected


def process_jee_main_schema_c(image, schema):
    debug = image.copy()
    result = {}

    # Roll number
    roll_number, roll_debug = read_roll_number(
        image,
        schema["roll_number"]
    )

    # Part I/II/III MCQ questions: Q1-20, Q31-50, Q61-80.
    for subject_name, subject in schema["subjects"].items():

        start_question = subject["start_question"]

        for row, y in enumerate(subject["y_positions"]):

            question_number = start_question + row

            answer, scores = read_choice_question(
                image,
                subject["x_positions"],
                y,
                schema["options"]
            )

            result[str(question_number)] = answer

            if answer in schema["options"]:
                index = schema["options"].index(answer)

                cv2.circle(
                    debug,
                    (
                        subject["x_positions"][index],
                        y
                    ),
                    10,
                    (255, 0, 0),
                    2
                )

    # Numerical questions: Q21-30, Q51-60, Q81-90.
    for numeric in schema["numeric_questions"]:

        answer, selected = read_schema_c_numeric_question(
            image,
            numeric["x_positions"],
            numeric["y_positions"]
        )

        question_number = numeric["start_question"]

        result[str(question_number)] = answer

    expected_questions = set(
        str(i)
        for i in range(1, 91)
    )

    if set(result.keys()) != expected_questions:
        missing = sorted(
            expected_questions - set(result.keys()),
            key=int
        )

        raise ValueError(
            "JEE Main Schema C extraction did not produce "
            f"all 90 questions. Missing: {missing}"
        )

    return result, debug, roll_number



# ============================================================
# JEE MAIN SCHEMA D  (blue ink, 75 questions)
# ============================================================
# The Schema D sheet is filled with BLUE ink (light blue in the
# numerical grids), so the "all BGR channels dark" test used by
# the other schemas would miss it. Schema D therefore measures
# darkness on the grayscale image, which treats navy and blue
# ink as dark and leaves the white bubble interiors alone.
#
# Every bubble is also tested at a few tiny shifts and the best
# score is kept, so a slightly tilted scan still reads correctly.

INK_GRAY_MAX = 120
SCHEMA_D_FILLED_THRESHOLD = 0.60


def ink_ratio_gray(
    gray,
    x,
    y,
    rx=5,
    ry=5,
    shift_x=(-2, 0, 2),
    shift_y=(-2, 0, 2),
):
    """Fraction of dark pixels inside an ellipse (best of a few shifts)."""
    h, w = gray.shape[:2]
    best = 0.0

    for dy in shift_y:
        for dx in shift_x:
            cx = int(round(x)) + dx
            cy = int(round(y)) + dy

            x1 = max(0, cx - rx)
            x2 = min(w, cx + rx + 1)
            y1 = max(0, cy - ry)
            y2 = min(h, cy + ry + 1)

            roi = gray[y1:y2, x1:x2]

            if roi.size == 0:
                continue

            yy, xx = np.ogrid[:roi.shape[0], :roi.shape[1]]
            mask = (
                ((xx - (cx - x1)) / float(rx)) ** 2 +
                ((yy - (cy - y1)) / float(ry)) ** 2
            ) <= 1.0

            pixels = roi[mask]

            if pixels.size == 0:
                continue

            best = max(best, float(np.mean(pixels < INK_GRAY_MAX)))

    return best


def read_roll_number_schema_d(gray, roll_schema):
    """7 columns x digits 0-9 (square bubbles)."""
    digits = []

    for x in roll_schema["x_positions"]:
        scores = [
            ink_ratio_gray(
                gray, x, y,
                rx=5, ry=6,
                shift_x=(-2, 0, 2),
                shift_y=(-2, 0, 2),
            )
            for y in roll_schema["digit_y_positions"]
        ]

        marked = [
            digit
            for digit, score in enumerate(scores)
            if score >= SCHEMA_D_FILLED_THRESHOLD
        ]

        if not marked:
            digits.append(None)
        elif len(marked) > 1:
            digits.append("INVALID")
        else:
            digits.append(str(marked[0]))

    if any(d in (None, "INVALID") for d in digits):
        return None, digits

    return "".join(digits), digits


def read_schema_d_numeric_question(gray, block):
    """
    One numerical answer: 4 digit columns + a minus bubble.

    Each digit column is two bubble columns side by side:
      left  column, rows 0-4 -> digits 0-4
      right column, rows 0-4 -> digits 5-9
    Blank digit columns are skipped when the answer is assembled.
    """
    xs = block["x_positions"]
    ys = block["y_positions"]
    digits = []

    for d in range(4):
        left_x = xs[2 * d]
        right_x = xs[2 * d + 1]
        marked = []

        for row, y in enumerate(ys):
            if ink_ratio_gray(
                gray, left_x, y,
                rx=3, ry=6,
                shift_x=(-1, 0, 1),
                shift_y=(-2, 0, 2),
            ) >= SCHEMA_D_FILLED_THRESHOLD:
                marked.append(row)

            if ink_ratio_gray(
                gray, right_x, y,
                rx=3, ry=6,
                shift_x=(-1, 0, 1),
                shift_y=(-2, 0, 2),
            ) >= SCHEMA_D_FILLED_THRESHOLD:
                marked.append(row + 5)

        if not marked:
            digits.append("")
        elif len(marked) > 1:
            digits.append("INVALID")
        else:
            digits.append(str(marked[0]))

    minus_x, minus_y = block["minus"]
    negative = ink_ratio_gray(
        gray, minus_x, minus_y,
        rx=3, ry=6,
        shift_x=(-1, 0, 1),
        shift_y=(-2, 0, 2),
    ) >= SCHEMA_D_FILLED_THRESHOLD

    if "INVALID" in digits:
        return "INVALID", digits, negative

    text = "".join(digits)

    if not text:
        # Nothing marked (a lone minus sign is not a valid answer).
        return ("INVALID" if negative else None), digits, negative

    return ("-" + text if negative else text), digits, negative


def process_jee_main_schema_d(image, schema):
    debug = image.copy()
    result = {}
    options = schema["options"]

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Roll number (7-column grid).
    roll_number, _roll_debug = read_roll_number_schema_d(
        gray,
        schema["roll_number"]
    )

    # MCQ blocks: Q1-20, Q26-45, Q51-70.
    for block in schema["mcq_blocks"]:
        for row, y in enumerate(block["y_positions"]):
            question_number = block["start_question"] + row

            scores = [
                ink_ratio_gray(gray, x, y, rx=5, ry=5)
                for x in block["x_positions"]
            ]

            marked = [
                i for i, score in enumerate(scores)
                if score >= SCHEMA_D_FILLED_THRESHOLD
            ]

            if not marked:
                answer = None
            elif len(marked) > 1:
                answer = "INVALID"
            else:
                answer = options[marked[0]]

            result[str(question_number)] = answer

            if answer in options:
                index = options.index(answer)
                cv2.circle(
                    debug,
                    (block["x_positions"][index], y),
                    10,
                    (0, 200, 0),
                    2
                )

    # Numerical questions: Q21-25, Q46-50, Q71-75.
    for block in schema["numeric_blocks"]:
        answer, _digits, _neg = read_schema_d_numeric_question(
            gray,
            block
        )

        result[str(block["question"])] = answer

    expected_questions = {str(i) for i in range(1, 76)}

    if set(result.keys()) != expected_questions:
        missing = sorted(
            expected_questions - set(result.keys()),
            key=int
        )

        raise ValueError(
            "JEE Main Schema D extraction did not produce "
            f"all 75 questions. Missing: {missing}"
        )

    # Keep answers in question order (1, 2, 3 ... 75).
    result = {
        str(i): result[str(i)]
        for i in range(1, 76)
    }

    return result, debug, roll_number


# ============================================================
# JEE ADVANCED  (magenta print, black / blue ink)
# ============================================================
# The JEE Advanced sheet is printed in magenta and may be filled
# with black OR blue ink. A pixel counts as ink when its RED
# channel is low: magenta print always has a high red channel,
# while black and blue ink both have a low one. Every bubble is
# tested at a few tiny shifts (best score kept) so a slightly
# tilted scan still reads correctly.

ADV_INK_RED_MAX = 120
ADV_FILLED_THRESHOLD = 0.35


def ink_ratio_advanced(image, x, y, radius=5, shifts=(-2, 0, 2)):
    """Fraction of ink pixels inside a circle (best of a few shifts)."""
    h, w = image.shape[:2]
    best = 0.0

    for dy in shifts:
        for dx in shifts:
            cx = int(round(x)) + dx
            cy = int(round(y)) + dy

            x1 = max(0, cx - radius)
            x2 = min(w, cx + radius + 1)
            y1 = max(0, cy - radius)
            y2 = min(h, cy + radius + 1)

            roi = image[y1:y2, x1:x2]

            if roi.size == 0:
                continue

            yy, xx = np.ogrid[:roi.shape[0], :roi.shape[1]]
            mask = (
                (xx - (cx - x1)) ** 2 +
                (yy - (cy - y1)) ** 2
            ) <= radius ** 2

            pixels = roi[mask]

            if pixels.size == 0:
                continue

            # OpenCV is BGR -> channel 2 is red.
            best = max(
                best,
                float(np.mean(pixels[:, 2] < ADV_INK_RED_MAX))
            )

    return best


def read_roll_number_advanced(image, roll_schema):
    """8 columns x digits 0-9."""
    digits = []

    for x in roll_schema["x_positions"]:
        marked = [
            digit
            for digit, y in enumerate(roll_schema["digit_y_positions"])
            if ink_ratio_advanced(image, x, y, radius=4)
            >= ADV_FILLED_THRESHOLD
        ]

        if not marked:
            digits.append(None)
        elif len(marked) > 1:
            digits.append("INVALID")
        else:
            digits.append(str(marked[0]))

    if any(d in (None, "INVALID") for d in digits):
        return None, digits

    return "".join(digits), digits


def read_advanced_numeric_question(image, block, numeric_options):
    """
    One numerical answer: 5 columns x 12 rows ('-', '.', 0-9).

    Blank columns are skipped and the marked characters are
    joined left to right, e.g. "-12.5".
    """
    selected = []

    for x in block["x_positions"]:
        marked = [
            i
            for i, y in enumerate(block["y_positions"])
            if ink_ratio_advanced(image, x, y, radius=4)
            >= ADV_FILLED_THRESHOLD
        ]

        if not marked:
            selected.append("")
        elif len(marked) > 1:
            selected.append("INVALID")
        else:
            selected.append(numeric_options[marked[0]])

    if all(value == "" for value in selected):
        return None

    if "INVALID" in selected:
        return "INVALID"

    text = "".join(selected)

    # A sheet with only '-' / '.' marked has no numeric value.
    if not any(ch.isdigit() for ch in text):
        return "INVALID"

    return text


def process_jee_advanced(image, schema):
    debug = image.copy()
    result = {}
    options = schema["options"]

    roll_number, _roll_debug = read_roll_number_advanced(
        image,
        schema["roll_number"]
    )

    # Section A and Section C: both allow more than one marked option.
    for block in schema["mcq_blocks"]:
        multi = block.get("multi_correct", False)

        for row, y in enumerate(block["y_positions"]):
            question_number = block["start_question"] + row

            marked = [
                i
                for i, x in enumerate(block["x_positions"])
                if ink_ratio_advanced(image, x, y, radius=5)
                >= ADV_FILLED_THRESHOLD
            ]

            if not marked:
                answer = None
            elif multi:
                # Multi-correct answers are stored as one string
                # in option order ("AC"), so the answer key and the
                # student sheet compare exactly.
                answer = "".join(options[i] for i in marked)
            elif len(marked) > 1:
                answer = "INVALID"
            else:
                answer = options[marked[0]]

            result[str(question_number)] = answer

            for i in marked:
                cv2.circle(
                    debug,
                    (block["x_positions"][i], y),
                    10,
                    (0, 200, 0),
                    2
                )

    # Section B numerical answers.
    for block in schema["numeric_blocks"]:
        result[str(block["question"])] = read_advanced_numeric_question(
            image,
            block,
            schema["numeric_options"]
        )

    total = schema.get("total_questions", 54)
    expected_questions = {str(i) for i in range(1, total + 1)}

    if set(result.keys()) != expected_questions:
        missing = sorted(
            expected_questions - set(result.keys()),
            key=int
        )

        raise ValueError(
            "JEE Advanced extraction did not produce "
            f"all {total} questions. Missing: {missing}"
        )

    # Keep answers in question order (1, 2, 3 ... 54).
    result = {str(i): result[str(i)] for i in range(1, total + 1)}

    return result, debug, roll_number


# ============================================================
# NEET
# ============================================================

def process_neet(image, schema):
    debug = image.copy()
    result = {}

    options = schema["options"]

    # --------------------------------------------------------
    # Read NEET Roll Number separately.
    # This does NOT modify the existing Q1-Q200 extraction.
    # --------------------------------------------------------
    roll_number, roll_debug = read_roll_number(
        image,
        schema["roll_number"]
    )

    print("\n" + "=" * 40)
    print("ROLL NUMBER")
    print("=" * 40)
    print(f"Roll Number: {roll_number}")
    print(f"Roll Number columns: {roll_debug}")

    # --------------------------------------------------------
    # NEET question extraction
    #
    # Schema A uses top_y_positions + bottom_y_positions.
    # Schema B uses one exact y_positions list and explicit
    # question_numbers because the supplied Schema B template
    # has 41 physical rows per block.
    # --------------------------------------------------------
    for column in schema["columns"]:

        if "question_numbers" in column:
            question_numbers = column["question_numbers"]
            y_positions = column["y_positions"]

            if len(question_numbers) != len(y_positions):
                raise ValueError(
                    "NEET schema question_numbers and y_positions "
                    "must have the same length."
                )

            for question_number, y in zip(
                question_numbers,
                y_positions
            ):
                answer, scores = read_choice_question(
                    image,
                    column["x_positions"],
                    y,
                    options
                )

                result[str(question_number)] = answer

                if answer in options:
                    index = options.index(answer)
                    cv2.circle(
                        debug,
                        (
                            column["x_positions"][index],
                            y
                        ),
                        8,
                        (255, 0, 0),
                        2
                    )

        else:
            # Existing Schema A.
            start_question = column["start_question"]

            for row, y in enumerate(
                column["top_y_positions"]
            ):
                question_number = start_question + row

                answer, scores = read_choice_question(
                    image,
                    column["x_positions"],
                    y,
                    options
                )

                result[str(question_number)] = answer

                if answer in options:
                    index = options.index(answer)
                    cv2.circle(
                        debug,
                        (
                            column["x_positions"][index],
                            y
                        ),
                        8,
                        (255, 0, 0),
                        2
                    )

            for row, y in enumerate(
                column["bottom_y_positions"]
            ):
                question_number = (
                    start_question + 35 + row
                )

                answer, scores = read_choice_question(
                    image,
                    column["x_positions"],
                    y,
                    options
                )

                result[str(question_number)] = answer

                if answer in options:
                    index = options.index(answer)
                    cv2.circle(
                        debug,
                        (
                            column["x_positions"][index],
                            y
                        ),
                        8,
                        (255, 0, 0),
                        2
                    )

    total_questions = schema.get("total_questions", 200)
    expected = {str(i) for i in result.keys()}

    if len(result) != total_questions:
        raise ValueError(
            f"NEET extraction produced {len(result)} questions, "
            f"but schema expects {total_questions}."
        )

    return result, debug, roll_number


# ============================================================
# Save JSON
# ============================================================

def save_json(result, exam_name, roll_number=None):
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

    output = {
        "exam": exam_name,
        "total_questions": len(result),
        "answered": answered,
        "blank": blank,
        "invalid": invalid,
        "roll_number": roll_number,
        "answers": result
    }

    # --------------------------------------------------------
    # Save filename:
    #
    #   54321_jee_mains.json
    #   2307564128_neet.json
    #   123456_jee_advanced.json
    #
    # The roll number is taken from the detected OMR bubbles.
    # --------------------------------------------------------
    exam_file_names = {
        "JEE Main": "jee_mains",
        "JEE Advanced": "jee_advanced",
        "NEET": "neet",
    }

    exam_file_name = exam_file_names.get(
        exam_name,
        exam_name.lower().replace(" ", "_")
    )

    if roll_number not in (None, "", "INVALID"):
        output_filename = f"{roll_number}_{exam_file_name}.json"
    else:
        output_filename = f"unknown_{exam_file_name}.json"

    with open(
        output_filename,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            output,
            f,
            indent=4,
            ensure_ascii=False
        )

    print("\n" + "=" * 60)
    print("JSON SAVED")
    print("=" * 60)
    print(json.dumps(output, indent=4))
    print(f"\nFile: {output_filename}")


# ============================================================
# Main
# ============================================================

def main():
    choice = select_omr_type()

    if choice == "1":
        schema_variant = select_jee_main_schema()
        schema = JEE_MAIN_SCHEMAS[schema_variant]
        print(f"\nSelected: JEE Main - Schema {schema_variant}")

    elif choice == "2":
        schema_variant = select_neet_schema()
        schema = NEET_SCHEMAS[schema_variant]
        print(f"\nSelected: NEET - Schema {schema_variant}")

    elif choice == "3":
        schema_variant = select_jee_advanced_schema()
        schema = JEE_ADVANCED_SCHEMAS[schema_variant]
        print(f"\nSelected: JEE Advanced - Schema {schema_variant}")

    else:
        raise ValueError("Unknown OMR type.")

    image_path = get_image_path()

    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(
            "OpenCV could not read the image."
        )

    print(
        f"Original image: "
        f"{image.shape[1]} x {image.shape[0]}"
    )

    image = resize_to_template(
        image,
        schema
    )

    if choice == "1":
        result, debug, roll_number = process_jee_main(
            image,
            schema
        )

    elif choice == "2":
        result, debug, roll_number = process_neet(
            image,
            schema
        )

    elif choice == "3":
        result, debug, roll_number = process_jee_advanced(
            image,
            schema
        )

    else:
        raise ValueError(
            "Unknown OMR type."
        )

    save_json(
        result,
        schema["name"],
        roll_number
    )

    cv2.imwrite(
        "omr_debug.png",
        debug
    )

    print("\nFile: omr_debug.png")


if __name__ == "__main__":
    main()