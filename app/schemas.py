# schemas.py
#
# OMR format definitions.
# Each exam has its own exact geometry and response structure.

JEE_MAIN_SCHEMA_A = {
    "name": "JEE Main",
    "template_width": 1024,
    "template_height": 1536,
    "options": ["A", "B", "C", "D"],

    # --------------------------------------------------------
    # JEE Main Roll Number
    # --------------------------------------------------------
    # 7 roll-number columns, each containing digits 0-9.
    # These coordinates are for the supplied 1024x1536 template.
    "roll_number": {
        "length": 7,
        "x_positions": [405, 425, 445, 465, 485, 505, 525],
        "digit_y_positions": [
            453, 473, 493, 513, 533,
            553, 573, 593, 613, 633
        ],
    },

    "subjects": {
        "Physics": {
            "start_question": 1,
            "x_positions": [137, 189, 241, 293],
            "y_positions": [
                720, 750, 779, 810, 841, 871, 901, 932, 962, 993,
                1024, 1054, 1085, 1116, 1146, 1177, 1208, 1238,
                1269, 1299, 1330, 1361, 1391, 1422, 1454
            ],
        },
        "Chemistry": {
            "start_question": 26,
            "x_positions": [459, 511, 563, 615],
            "y_positions": [
                720, 750, 779, 810, 841, 871, 901, 932, 962, 993,
                1024, 1054, 1085, 1116, 1146, 1177, 1208, 1238,
                1269, 1299, 1330, 1361, 1391, 1422, 1454
            ],
        },
        "Mathematics": {
            "start_question": 51,
            "x_positions": [779, 832, 886, 938],
            "y_positions": [
                720, 750, 779, 810, 841, 871, 901, 932, 962, 993,
                1024, 1054, 1085, 1116, 1146, 1177, 1208, 1238,
                1269, 1299, 1330, 1361, 1391, 1422, 1454
            ],
        },
    },
}




# ============================================================
# JEE MAIN - SCHEMA B
# ============================================================
# Alternate JEE Main template.
# A = existing JEE Main template
# B = new JEE Main template
#
# B has:
#   Physics   Q1-Q30
#   Chemistry Q31-Q60
#   Maths     Q61-Q90
#   Roll No.  5 digit columns, each with 0-9
# ============================================================

JEE_MAIN_SCHEMA_B = {
    "name": "JEE Main",
    "template_width": 1087,
    "template_height": 1446,
    "options": ["A", "B", "C", "D"],

    "roll_number": {
        "length": 5,
        "x_positions": [488, 510, 536, 560, 584],
        "digit_y_positions": [
            502, 521, 540, 558, 577,
            595, 614, 632, 669, 688
        ],
    },

    "subjects": {
        "Physics": {
            "start_question": 1,
            "x_positions": [144, 204, 266, 327],
            "y_positions": [
                794, 814, 834, 854, 874, 893, 913, 933, 953, 974,
                994, 1014, 1033, 1053, 1073, 1093, 1113, 1134, 1154, 1174,
                1194, 1214, 1234, 1254, 1274, 1292, 1313, 1334, 1354, 1374
            ],
        },

        "Chemistry": {
            "start_question": 31,
            "x_positions": [463, 522, 586, 646],
            "y_positions": [
                794, 814, 834, 854, 874, 893, 913, 933, 953, 974,
                994, 1014, 1033, 1053, 1073, 1093, 1113, 1134, 1154, 1174,
                1194, 1214, 1234, 1254, 1274, 1292, 1313, 1334, 1354, 1374
            ],
        },

        "Mathematics": {
            "start_question": 61,
            "x_positions": [782, 844, 906, 966],
            "y_positions": [
                794, 814, 834, 854, 874, 893, 913, 933, 953, 974,
                994, 1014, 1033, 1053, 1073, 1093, 1113, 1134, 1154, 1174,
                1194, 1214, 1234, 1254, 1274, 1292, 1313, 1334, 1354, 1374
            ],
        },
    },
}
NEET_SCHEMA_A = {
    "name": "NEET",
    "template_width": 1083,
    "template_height": 1452,
    "options": ["1", "2", "3", "4"],

    # --------------------------------------------------------
    # NEET Roll Number
    # --------------------------------------------------------
    # 10 roll-number columns, each containing digits 0-9.
    # The bubble grid is read top-to-bottom as 0,1,2,...,9.
    # Coordinates are for the supplied 1083x1452 NEET template.
    "roll_number": {
        "length": 10,
        "x_positions": [112, 138, 164, 190, 216, 244, 270, 296, 322, 348],
        "digit_y_positions": [
            168, 190, 212, 236, 258,
            282, 304, 326, 350, 372
        ],
    },

    "columns": [
        {
            "start_question": 1,
            "x_positions": [473, 499, 525, 549],
            "top_y_positions": [
                98, 121, 144, 167, 190, 213, 236, 259, 281, 304,
                327, 350, 374, 397, 420, 442, 465, 489, 513, 536,
                559, 583, 605, 628, 651, 675, 699, 722, 745, 767,
                791, 814, 838, 861, 884
            ],
            "bottom_y_positions": [
                929, 952, 976, 999, 1022, 1045, 1067, 1090,
                1114, 1137, 1160, 1183, 1206, 1229, 1252
            ],
        },
        {
            "start_question": 51,
            "x_positions": [626, 651, 676, 701],
            "top_y_positions": [
                98, 121, 144, 167, 190, 213, 236, 259, 281, 304,
                327, 350, 373, 397, 419, 443, 466, 490, 513, 536,
                559, 582, 605, 628, 652, 675, 698, 722, 745, 768,
                791, 814, 837, 861, 883
            ],
            "bottom_y_positions": [
                930, 952, 976, 999, 1022, 1045, 1067, 1090,
                1113, 1136, 1160, 1183, 1205, 1228, 1252
            ],
        },
        {
            "start_question": 101,
            "x_positions": [781, 806, 831, 856],
            "top_y_positions": [
                98, 121, 145, 167, 190, 213, 236, 259, 281, 304,
                327, 350, 374, 397, 421, 443, 466, 490, 513, 537,
                560, 583, 605, 628, 652, 675, 699, 722, 745, 768,
                791, 814, 837, 861, 884
            ],
            "bottom_y_positions": [
                929, 952, 976, 999, 1022, 1045, 1067, 1090,
                1114, 1137, 1160, 1183, 1206, 1228, 1252
            ],
        },
        {
            "start_question": 151,
            "x_positions": [935, 961, 986, 1010],
            "top_y_positions": [
                98, 121, 145, 167, 190, 213, 236, 259, 281, 304,
                327, 350, 374, 398, 420, 443, 466, 490, 513, 537,
                560, 583, 605, 628, 651, 675, 698, 722, 745, 768,
                791, 814, 838, 861, 884
            ],
            "bottom_y_positions": [
                929, 952, 976, 999, 1022, 1045, 1067, 1090,
                1114, 1137, 1160, 1183, 1207, 1229, 1252
            ],
        },
    ],
}

# ============================================================
# NEET - SCHEMA B
# ============================================================
# Exact geometry of the uploaded NEET Schema B image.
#
# IMPORTANT:
# The supplied image is 1090 x 1443 and physically contains
# 41 response rows in EACH response block, not 45.
# Therefore this schema reads the 164 physical response rows
# that actually exist in the supplied image.
#
# The printed labels say 1-45, 46-90, 91-135 and 136-180,
# but several printed question labels are duplicated/missing.
# We do NOT invent missing bubble rows or silently shift answers.
# The physical rows are mapped sequentially:
#   block 1 -> Q1-Q41
#   block 2 -> Q46-Q86
#   block 3 -> Q91-Q131
#   block 4 -> Q136-Q176
#
# To support a true Q1-Q180 extraction, the source template must
# contain 45 physical bubble rows in every block.
# ============================================================

NEET_SCHEMA_B = {
    "name": "NEET",

    # Exact dimensions of the supplied NEET Schema-B image.
    "template_width": 646,
    "template_height": 856,

    # Response bubbles are printed as 1, 2, 3, 4.
    "options": ["1", "2", "3", "4"],

    # This template contains 4 response blocks with
    # 45 physical rows in each block:
    #   Block 1 -> Q1-Q45
    #   Block 2 -> Q46-Q90
    #   Block 3 -> Q91-Q135
    #   Block 4 -> Q136-Q180
    "total_questions": 180,
    "physical_rows_per_block": 45,

    # --------------------------------------------------------
    # Roll Number
    # --------------------------------------------------------
    # The supplied image has 5 roll-number columns.
    # Each column contains digits 0-9 from top to bottom.
    "roll_number": {
        "length": 5,

        # Centers of the 5 roll-number columns.
        "x_positions": [47, 70, 93, 116, 139],

        # Digit rows: 0,1,2,...,9.
        "digit_y_positions": [
            113, 126, 138, 151, 163,
            176, 188, 201, 213, 226
        ],
    },

    # --------------------------------------------------------
    # Response blocks
    # --------------------------------------------------------
    # The four blocks have the same 45 y positions.
    # Only the x positions change from block to block.
    "columns": [
        {
            "start_question": 1,
            "x_positions": [75, 99, 123, 147],
            "question_numbers": list(range(1, 46)),
            "y_positions": [
                260, 273, 285, 297, 309, 322, 334, 346, 358,
                371, 383, 395, 407, 420, 432, 444, 456, 469,
                481, 493, 505, 518, 530, 542, 554, 567, 579,
                591, 603, 616, 628, 640, 653, 665, 677, 690,
                702, 714, 726, 739, 751, 763, 776, 788, 801
            ],
        },
        {
            "start_question": 46,
            "x_positions": [222, 246, 270, 294],
            "question_numbers": list(range(46, 91)),
            "y_positions": [
                260, 273, 285, 297, 309, 322, 334, 346, 358,
                371, 383, 395, 407, 420, 432, 444, 456, 469,
                481, 493, 505, 518, 530, 542, 554, 567, 579,
                591, 603, 616, 628, 640, 653, 665, 677, 690,
                702, 714, 726, 739, 751, 763, 776, 788, 801
            ],
        },
        {
            "start_question": 91,
            "x_positions": [369, 393, 417, 441],
            "question_numbers": list(range(91, 136)),
            "y_positions": [
                260, 273, 285, 297, 309, 322, 334, 346, 358,
                371, 383, 395, 407, 420, 432, 444, 456, 469,
                481, 493, 505, 518, 530, 542, 554, 567, 579,
                591, 603, 616, 628, 640, 653, 665, 677, 690,
                702, 714, 726, 739, 751, 763, 776, 788, 801
            ],
        },
        {
            "start_question": 136,
            "x_positions": [516, 540, 564, 588],
            "question_numbers": list(range(136, 181)),
            "y_positions": [
                260, 273, 285, 297, 309, 322, 334, 346, 358,
                371, 383, 395, 407, 420, 432, 444, 456, 469,
                481, 493, 505, 518, 530, 542, 554, 567, 579,
                591, 603, 616, 628, 640, 653, 665, 677, 690,
                702, 714, 726, 739, 751, 763, 776, 788, 801
            ],
        },
    ],
}



# JEE Main variants. The user selects JEE Main first, then A or B.
JEE_MAIN_SCHEMAS = {
    "A": JEE_MAIN_SCHEMA_A,
    "B": JEE_MAIN_SCHEMA_B,
}

# NEET variants. The user selects NEET first, then A or B.
NEET_SCHEMAS = {
    "A": NEET_SCHEMA_A,
    "B": NEET_SCHEMA_B,
}

# Exam selection:
# 1 = JEE Main
# 2 = NEET
SCHEMAS = {
    "1": JEE_MAIN_SCHEMA_A,
    "2": NEET_SCHEMA_A,
}
