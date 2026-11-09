from rag.ingestion.chunker import chunk_pages


def texts(pages):
    return [chunk.text for chunk in chunk_pages("handbook.pdf", pages)]


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


def test_headings_carry_over_to_the_next_page():
    pages = [
        (1, "7. Course Catalogue\nCS211: Operating Systems\nThe operating system serves as an interface."),
        (2, "It covers processes, threads and memory.\nPrerequisites: CS201"),
    ]

    assert texts(pages)[-1] == (
        "7. Course Catalogue > CS211: Operating Systems\nIt covers processes, threads and memory.\nPrerequisites: CS201"
    )


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


def test_numbered_sentences_and_table_of_contents_lines_are_not_headings():
    page = (
        "1. Demonstrate an understanding of fundamental computer science\n"
        "2 ELECTIVES\n"
        "4. Program Structure and Curriculum ........................ 6\n"
    )

    assert texts([(1, page)]) == [page.strip()]


def test_text_without_headings_is_unchanged():
    assert texts([(1, "Office hours are on Tuesday.")]) == ["Office hours are on Tuesday."]
