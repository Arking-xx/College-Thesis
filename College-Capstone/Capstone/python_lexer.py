import re

# Define token types with regex patterns
TOKEN_TYPES = [
    ('STRING', r"(?<!\\)('(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\")"),# String literals with single or double quotes
    ('KEYWORD', r'\b(?:print|input|while|for|if|elif|else)\b'),# Python keywords
    ('IDENTIFIER', r'[a-zA-Z_][a-zA-Z0-9_]*'),        # Variable/function names
    ('COMPARISON_OPERATOR', r'[<>]=?|==|!=|>=|<='),   # Comparison operators
    ('ARITHMETIC_OPERATOR', r'[+\-*/%]'),             # Arithmetic operators
    ('ASSIGNMENT_OPERATOR', r'='),                    # Assignment operator
    ('LOGICAL_OPERATOR', r'&&|\|\|'),           # Logical operators (C++ style)
    ('BITWISE_OPERATOR', r'&|\||~|^'),                # Bitwise operators
    ('LPAREN', r'\('),                                # Left parenthesis
    ('RPAREN', r'\)'),                                # Right parenthesis
    ('WHITESPACE', r'\s+'),                         # Whitespace (ignored)
    ('COLON', r':'),                                # Colon for Python blocks
    ('NUMBER', r'\d+(\.\d*)?'),                      # Integer or float numbers
    ('COMMA', r','),                            # Comma for argument separation
]

# Lexer class to tokenize Python-like source code
class PythonLexer:
    def __init__(self):
        # Compile regex patterns for each token type
        self.token_types = [(name, re.compile(pattern)) for name, pattern in TOKEN_TYPES]

    # Convert source string into a list of tokens
    def tokenize(self, source):
        position = 0  # Current position in source string
        tokens = []   # List to store token tuples (type, value)
        while position < len(source):
            match = None
            # Try matching each token type at current position
            for name, pattern in self.token_types:
                match = pattern.match(source, position)
                if match:
                    if name != 'WHITESPACE':  # Skip whitespace tokens
                        # Add token type and matched string to list
                        tokens.append((name, match.group(0)))
                    position = match.end()  # Move position to end of match
                    break
            if not match:
                # Debug info and error if no token matches
                print(f"No match found at position {position}, text: {source[position:position+10]}")
                raise ValueError(f"Unable to tokenize at position {position}")
        return tokens  # Return list of tokens