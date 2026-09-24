# omr_reader.py

import cv2
import numpy as np
import json
import os

from app.schemas import SCHEMAS, JEE_MAIN_SCHEMAS, NEET_SCHEMAS


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

    while True:
        choice = input("\nEnter option (1/2): ").strip()

        if choice in SCHEMAS:
            return choice

        print("Invalid choice. Enter 1 or 2.")


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

    while True:
        variant = input("\nEnter schema (A/B): ").strip().upper()

        if variant in JEE_MAIN_SCHEMAS:
            return variant

        print("Invalid choice. Enter A or B.")


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

    while True:
        variant = input("\nEnter schema (A/B): ").strip().upper()

        if variant in NEET_SCHEMAS:
            return variant

        print("Invalid choice. Enter A or B.")



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
