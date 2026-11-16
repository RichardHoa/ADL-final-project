from rag.ingestion.chunker import chunk_pages


def texts(pages):
    return [chunk.text for chunk in chunk_pages("handbook.pdf", pages)]


def pages_and_texts(pages):
    return [(chunk.pages, chunk.text) for chunk in chunk_pages("handbook.pdf", pages)]


def test_chunks_are_prefixed_with_the_headings_they_sit_under():
    page = (
        "5. Concentrations in the Computer Science Major\n"
        "5.2 Available Concentrations\n"
        "5.2.2 Artificial Intelligence\n"
        "• CS307 Machine Learning\n"
        "• CS312 Natural Language Processing\n"
    )

    assert texts([(1, page)]) == [
        "5. Concentrations in the Computer Science Major > 5.2 Available Concentrations > 5.2.2 Artificial Intelligence\n"
        "• CS307 Machine Learning\n• CS312 Natural Language Processing"
    ]


def test_a_section_spanning_two_pages_is_one_chunk_listing_both_pages():
    pages = [
        (1, "7. Course Catalogue\nCS211: Operating Systems\nThe operating system serves as an interface."),
        (2, "It covers processes, threads and memory.\nPrerequisites: CS201"),
    ]

    assert pages_and_texts(pages) == [
        (
            (1, 2),
            "7. Course Catalogue > CS211: Operating Systems\nThe operating system serves as an interface.\n"
            "It covers processes, threads and memory.\nPrerequisites: CS201",
        )
    ]


def test_a_new_heading_starts_a_new_chunk_and_replaces_its_siblings():
    page = (
        "7. Course Catalogue\n"
        "CS101: Introduction to Programming\nBranching, loops and functions.\n"
        "CS3xx: Bioinformatics\nSequence alignment.\n"
        "APPENDIX I\nGraduate schools.\n"
    )

    assert texts([(1, page)]) == [
        "7. Course Catalogue > CS101: Introduction to Programming\nBranching, loops and functions.",
        "7. Course Catalogue > CS3xx: Bioinformatics\nSequence alignment.",
        "APPENDIX I\nGraduate schools.",
    ]


def test_numbered_sentences_are_not_headings():
    page = "1. Demonstrate an understanding of fundamental computer science\n2 ELECTIVES\n"

    assert texts([(1, page)]) == [page.strip()]


def test_table_of_contents_lines_are_dropped():
    page = (
        "Contents\n"
        "4. Program Structure and Curriculum ........................ 6\n"
        "Major Requirements (56 credits) ............................ 7\n"
        "7. Course Catalogue........................................ 14\n"
    )

    assert texts([(1, page)]) == ["Contents"]


def test_text_without_headings_is_unchanged():
    assert texts([(1, "Office hours are on Tuesday.")]) == ["Office hours are on Tuesday."]


TABLE_OF_CONTENTS = (
    "4. Program Structure and Curriculum ........................ 6\n"
    "Degree Requirements ........................................ 6\n"
    "General Curriculum Requirements (40 credits & 10 noncredit items)  ......... 6\n"
    "Major Requirements (56 credits) ............................ 7\n"
    "Minor Requirements (24 credits) ............................ 7\n"
    "5. Concentrations in the Computer Science Major ............ 11\n"
    "5.2 Available Concentrations ............................... 11\n"
    "Concentration Advisors ..................................... 12\n"
)


def test_table_of_contents_headings_split_sections_and_nest_under_the_numbered_heading_above_them():
    body = (
        "4. Program Structure and Curriculum\n"
        "Every program has several components.\n"
        "Major Requirements (56 credits)\n"
        "• CS 101: Introduction to Programming (4 credits)\n"
        "Minor Requirements (24 credits)\n"
        "The minor requires six courses.\n"
        "5. Concentrations in the Computer Science Major\n"
        "5.2 Available Concentrations\n"
        "Concentration Advisors\n"
        "Ask the program coordinator.\n"
    )

    assert texts([(1, TABLE_OF_CONTENTS), (2, body)]) == [
        "4. Program Structure and Curriculum\nEvery program has several components.",
        "4. Program Structure and Curriculum > Major Requirements (56 credits)\n"
        "• CS 101: Introduction to Programming (4 credits)",
        "4. Program Structure and Curriculum > Minor Requirements (24 credits)\nThe minor requires six courses.",
        "5. Concentrations in the Computer Science Major > 5.2 Available Concentrations > Concentration Advisors\n"
        "Ask the program coordinator.",
    ]


def test_a_table_of_contents_heading_matches_with_extra_spaces_and_a_trailing_footnote_number():
    body = (
        "4. Program Structure and Curriculum\n"
        "General Curriculum  Requirements (40 credits & 10 noncredit items) 1\n"
        "• 4 Core courses (16 credits)\n"
    )

    assert texts([(1, TABLE_OF_CONTENTS), (2, body)]) == [
        "4. Program Structure and Curriculum > General Curriculum Requirements (40 credits & 10 noncredit items)\n"
        "• 4 Core courses (16 credits)",
    ]


def test_a_long_section_splits_at_paragraphs_and_each_piece_lists_the_pages_it_spans():
    first, second, third = ("A" * 349 + ".", "B" * 349 + ".", "C" * 349 + ".")
    pages = [(1, f"6. Teaching, Learning, and Assessment\n{first}\n\n{second}\n"), (2, f"\n{third}\n")]

    assert pages_and_texts(pages) == [
        ((1,), f"6. Teaching, Learning, and Assessment\n{first}\n\n{second}"),
        ((2,), f"6. Teaching, Learning, and Assessment\n{third}"),
    ]


def test_a_long_paragraph_splits_at_sentence_ends_without_overlap():
    paragraph = " ".join(f"Sentence {number} describes one more assessment in some detail." for number in range(20))

    pieces = texts([(1, f"6. Teaching, Learning, and Assessment\n{paragraph}")])

    bodies = [piece.removeprefix("6. Teaching, Learning, and Assessment\n") for piece in pieces]
    assert len(bodies) == 2
    assert all(len(body) <= 750 and body.endswith("detail.") for body in bodies)
    assert " ".join(bodies) == paragraph


def test_empty_sections_produce_no_chunk_but_text_before_the_first_heading_does():
    pages = [
        (1, "Undergraduate Major Handbook\n"),
        (2, "5. Concentrations in the Computer Science Major\n\n5.2 Available Concentrations\n• CS307 Machine Learning\n"),
    ]

    assert pages_and_texts(pages) == [
        ((1,), "Undergraduate Major Handbook"),
        ((2,), "5. Concentrations in the Computer Science Major > 5.2 Available Concentrations\n• CS307 Machine Learning"),
    ]


def test_a_piece_crossing_a_page_break_lists_both_pages():
    first, second, third = ("A" * 349 + ".", "B" * 349 + ".", "C" * 349 + ".")
    pages = [(1, f"6. Teaching, Learning, and Assessment\n{first}\n\n{second[:200]}"), (2, f"{second[200:]}\n\n{third}\n")]

    assert [chunk.pages for chunk in chunk_pages("handbook.pdf", pages)] == [(1, 2), (2,)]


def test_each_chunk_records_its_heading_and_which_part_of_its_section_it_is():
    first, second, third = ("A" * 349 + ".", "B" * 349 + ".", "C" * 349 + ".")
    pages = [(1, f"Cover page\n6. Teaching, Learning, and Assessment\n{first}\n\n{second}\n\n{third}\n7. Policies\nBe kind.")]

    assert [(chunk.heading, chunk.part, chunk.parts) for chunk in chunk_pages("handbook.pdf", pages)] == [
        ("", 1, 1),
        ("6. Teaching, Learning, and Assessment", 1, 2),
        ("6. Teaching, Learning, and Assessment", 2, 2),
        ("7. Policies", 1, 1),
    ]
