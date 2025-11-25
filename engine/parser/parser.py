"""
Parser — Compact, Indentation-Based DSL Parser
===============================================
This converts the token stream into a full AST.
- Block structure is determined by indentation.
- Commands map directly into AST nodes.
- Expressions (SET left PLUS right) are parsed minimally.
"""

from typing import List
from engine.lexer.tokenizer import Token
from engine.parser.ast_nodes import (
    Program, Trigger,
    SetStmt, OutputStmt, RepeatStmt, IfStmt,
    CreateFileStmt, WriteFileStmt,
    Literal, Identifier, Stmt
)


# ============================================================
# Parser
# ============================================================

class Parser:
    def parse(self, tokens: List[Token]) -> Program:
        self.toks = tokens
        self.i = 0
        prog = Program(line=1)

        while not self.eof():
            tok = self.peek()
            if tok.type == "WHEN":
                prog.triggers.append(self.parse_trigger())
            else:
                self.advance()  # skip irrelevant tokens at top-level

        return prog

    # ----------------------------------------------------------
    # Trigger
    # ----------------------------------------------------------

    def parse_trigger(self) -> Trigger:
        when = self.expect("WHEN")
        name_tok = self.expect("IDENT")
        trig = Trigger(name=name_tok.value, line=when.line, block=[])

        # skip to next line / indent collected in statements
        base_indent = 0

        # read nested statements
        body = []
        while not self.eof():
            t = self.peek()
            if t.indent <= base_indent:
                break
            body.append(self.parse_statement())
        trig.block = body
        return trig

    # ----------------------------------------------------------
    # Statement dispatcher
    # ----------------------------------------------------------

    def parse_statement(self) -> Stmt:
        tok = self.peek()

        if tok.type == "SET":
            return self.parse_set()

        elif tok.type == "OUTPUT":
            return self.parse_output()

        elif tok.type == "REPEAT":
            return self.parse_repeat()

        elif tok.type == "IF":
            return self.parse_if()

        elif tok.type == "CREATE":
            return self.parse_create_file()

        elif tok.type == "WRITE":
            return self.parse_write_file()

        else:
            # skip unknown tokens
            self.advance()
            return Literal(line=tok.line, value=None)

    # ----------------------------------------------------------
    # Statements
    # ----------------------------------------------------------

    def parse_set(self) -> SetStmt:
        kw = self.expect("SET")
        target = self.expect("STRING").value.strip('"')

        self.expect("TO")
        left_tok = self.expect_any(["IDENT", "STRING", "NUMBER"])
        left = self.wrap_literal(left_tok)

        # arithmetic?
        if self.match("PLUS") or self.match("MINUS") or self.match("TIMES"):
            op = self.prev().type  # PLUS/MINUS/TIMES
            right_tok = self.expect_any(["IDENT", "STRING", "NUMBER"])
            right = self.wrap_literal(right_tok)
        else:
            op = None
            right = None

        return SetStmt(
            line=kw.line,
            target=target,
            op=op,
            left=left,
            right=right
        )

    def parse_output(self) -> OutputStmt:
        kw = self.expect("OUTPUT")
        val_tok = self.expect_any(["IDENT", "STRING", "NUMBER"])
        val = self.wrap_literal(val_tok)
        return OutputStmt(line=kw.line, value=val)

    def parse_repeat(self) -> RepeatStmt:
        kw = self.expect("REPEAT")
        count_tok = self.expect_any(["IDENT", "NUMBER"])
        count = self.wrap_literal(count_tok)

        self.expect("TIMES")
        base_indent = kw.indent

        body = []
        while not self.eof() and self.peek().indent > base_indent:
            body.append(self.parse_statement())

        return RepeatStmt(line=kw.line, count=count, body=body)

    def parse_if(self) -> IfStmt:
        kw = self.expect("IF")
        var = self.expect("STRING").value.strip('"')
        self.expect("IS")
        val_tok = self.expect_any(["STRING", "NUMBER", "IDENT"])
        expected = self.wrap_literal(val_tok)
        base_indent = kw.indent

        body = []
        while not self.eof() and self.peek().indent > base_indent:
            body.append(self.parse_statement())

        return IfStmt(line=kw.line, var=var, expected=expected, body=body)

    def parse_create_file(self) -> CreateFileStmt:
        kw = self.expect("CREATE")
        self.expect("FILE")
        name = self.expect("STRING").value.strip('"')
        return CreateFileStmt(line=kw.line, filename=name)

    def parse_write_file(self) -> WriteFileStmt:
        kw = self.expect("WRITE")
        content_tok = self.expect_any(["IDENT", "STRING", "NUMBER"])
        content = self.wrap_literal(content_tok)

        self.expect("TO")
        self.expect("FILE")
        fname = self.expect("STRING").value.strip('"')

        return WriteFileStmt(line=kw.line, filename=fname, content=content)

    # ----------------------------------------------------------
    # Token utilities
    # ----------------------------------------------------------

    def wrap_literal(self, tok: Token):
        if tok.type == "NUMBER":
            if "." in tok.value:
                return Literal(tok.line, float(tok.value))
            return Literal(tok.line, int(tok.value))

        if tok.type == "STRING":
            return Literal(tok.line, tok.value.strip('"'))

        return Identifier(tok.line, tok.value)

    def match(self, type_: str) -> bool:
        if not self.eof() and self.peek().type == type_:
            self.advance()
            return True
        return False

    def expect(self, type_: str) -> Token:
        tok = self.peek()
        if tok.type != type_:
            raise SyntaxError(f"Expected {type_} at line {tok.line}, got {tok.type}")
        return self.advance()

    def expect_any(self, types: List[str]) -> Token:
        tok = self.peek()
        if tok.type not in types:
            raise SyntaxError(f"Expected one of {types} at line {tok.line}, got {tok.type}")
        return self.advance()

    # ----------------------------------------------------------
    # Iterator helpers
    # ----------------------------------------------------------

    def peek(self) -> Token:
        return self.toks[self.i]

    def prev(self) -> Token:
        return self.toks[self.i - 1]

    def advance(self) -> Token:
        tok = self.toks[self.i]
        self.i += 1
        return tok

    def eof(self) -> bool:
        return self.i >= len(self.toks)
