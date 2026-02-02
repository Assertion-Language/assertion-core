"""
Hybrid Tokenizer — Compact & Enterprise Grade
=============================================
This tokenizer provides:
- Indentation tracking (block structure)
- Hybrid regex/DFA scanning
- Full keyword recognition
- String, number, identifier, symbol tokens
- Positioned tokens for parser/AST/diagnostics
"""

import re
from dataclasses import dataclass
from typing import List

# ------------------------------------------------------------
# Token Model
# ------------------------------------------------------------

@dataclass
class Token:
    type: str       # Token type (IDENT, NUMBER, WHEN, IF, STRING, etc.)
    value: str      # Lexeme text
    indent: int     # Leading indentation level
    line: int       # Line number


# ------------------------------------------------------------
# Token Definitions
# ------------------------------------------------------------

KEYWORDS = {
    "WHEN", "SET", "OUTPUT", "IF", "IS",
    "PLUS", "MINUS", "TIMES",
    "REPEAT", "TIMES",
    "CREATE", "WRITE", "TO", "FILE",
    "CALLED", "NAMED", "WITH", "VALUE"
}

SYNONYMS = {
    # SET
    "MAKE": "SET",
    "LET": "SET",
    "DEFINE": "SET",
    "ASSIGN": "SET",

    # OUTPUT
    "PRINT": "OUTPUT",
    "SAY": "OUTPUT",
    "WHISPER": "OUTPUT",
    "SHOUT": "OUTPUT",
    "DISPLAY": "OUTPUT",

    # REPEAT
    "LOOP": "REPEAT",
    "ITERATE": "REPEAT",

    # IS
    "EQUALS": "IS",
    "BE": "IS"
}

NOISE_WORDS = {
    "THE", "A", "AN",
    "PLEASE", "KINDLY", "NOW", "THEN",
    "DO", "IT", "AGAIN"
}

# Regex patterns
STRING = re.compile(r'"([^"\\]|\\.)*"')
NUMBER = re.compile(r"-?\d+(\.\d+)?")
IDENT  = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


# ------------------------------------------------------------
# Tokenizer Implementation
# ------------------------------------------------------------

def tokenize(text: str) -> List[Token]:
    """
    Compact hybrid tokenizer using regex + manual scanning.
    - Indentation preserved
    - Greedy matching for literals
    - Case-insensitive keyword handling
    """

    tokens = []
    lines = text.splitlines()

    for line_no, line in enumerate(lines, start=1):
        if not line.strip():
            continue  # skip blank lines

        indent = len(line) - len(line.lstrip())
        src = line.lstrip()
        i = 0
        n = len(src)

        while i < n:
            ch = src[i]

            # Skip whitespace within line
            if ch.isspace():
                i += 1
                continue

            # ------------------------------
            # STRINGS
            # ------------------------------
            m = STRING.match(src, i)
            if m:
                lex = m.group(0)
                tokens.append(Token("STRING", lex, indent, line_no))
                i = m.end()
                continue

            # ------------------------------
            # NUMBERS
            # ------------------------------
            m = NUMBER.match(src, i)
            if m:
                lex = m.group(0)
                tokens.append(Token("NUMBER", lex, indent, line_no))
                i = m.end()
                continue

            # ------------------------------
            # IDENTIFIERS / KEYWORDS
            # ------------------------------
            m = IDENT.match(src, i)
            if m:
                lex = m.group(0)
                upper = lex.upper()

                if upper in NOISE_WORDS:
                    # Skip noise words entirely
                    i = m.end()
                    continue

                if upper in KEYWORDS:
                    tokens.append(Token(upper, lex, indent, line_no))
                elif upper in SYNONYMS:
                    # Map synonym to canonical keyword
                    canonical = SYNONYMS[upper]
                    tokens.append(Token(canonical, lex, indent, line_no))
                else:
                    tokens.append(Token("IDENT", lex, indent, line_no))
                i = m.end()
                continue

            # ------------------------------
            # SYMBOLS (single character)
            # ------------------------------
            tokens.append(Token("SYMBOL", ch, indent, line_no))
            i += 1

    return tokens
