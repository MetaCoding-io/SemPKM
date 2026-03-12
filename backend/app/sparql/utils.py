"""SPARQL utility functions."""


def escape_sparql_regex(text: str) -> str:
    """Escape SPARQL regex metacharacters in user-supplied text.

    Ensures that user input containing regex-special characters is treated
    as literal text when injected into a SPARQL REGEX() filter.

    Escapes (in order): \\ " . * + ? ^ $ { } ( ) | [ ]
    """
    # Backslash must be escaped first to avoid double-escaping
    text = text.replace("\\", "\\\\")
    text = text.replace('"', '\\"')
    for ch in r". * + ? ^ $ { } ( ) | [ ]".split():
        text = text.replace(ch, f"\\{ch}")
    return text
