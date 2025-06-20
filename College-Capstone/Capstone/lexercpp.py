import re

# Define token types with regex patterns
TOKEN_TYPES = [
    ('KEYWORD', r'\b(int|float|double|bool|char|string|void|if|else|while|for|return|using|namespace|include)\b'),  # C++ keywords
    ('IDENTIFIER', r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'),  # Variable/function names
    ('NUMBER', r'\b\d+(\.\d*)?\b'),                  # Integer or float numbers
    ('INSERTION_OPERATOR', r'>>|<<'),                # C++ I/O operators
    ('RELATIONAL_OPERATOR', r'<=|>=|==|!=|<|>'),     # Comparison operators
    ('COMPOUND_ASSIGNMENT', r'\+=|-=|\*=|/='),   # Compound assignment operators
    ('ARITHMETIC_OPERATOR', r'\+\+|--|[+\-*/%=]'),   # Arithmetic operators including ++ and --
    ('STRING', r'"[^"\\]*(?:\\.[^"\\]*)*"'),         # String literals with escapes
    ('SEMICOLON', r';'),                             # Statement terminator
    ('COMMA', r','),                                 # Argument separator
    ('LBRACE', r'\{'),                               # Left brace
    ('RBRACE', r'\}'),                               # Right brace
    ('LPAREN', r'\('),                               # Left parenthesis
    ('RPAREN', r'\)'),                               # Right parenthesis
    ('SPECIAL_CHARACTER', r'[@_!#$^&?~]'),           # Special characters (unused typically)
    ('APOSTROPHE', r"'"),                            # Single quote (e.g., char literals)
    ('WHITESPACE', r'\s+'),                          # Whitespace (ignored)
]

# Lexer class to tokenize C++-like source code
class Lexer:
    def __init__(self, token_types=TOKEN_TYPES, keywords=None):
        # Extract keywords from TOKEN_TYPES if not provided
        if keywords is None:
            keyword_pattern = next((p for n, p in token_types if n == 'KEYWORD'), r'')
            self.keywords = set(re.findall(r'\w+', keyword_pattern))  # e.g., {'int', 'if', ...}
        else:
            self.keywords = set(keywords)  # Custom keyword set
        # Compile regex patterns for token matching
        self.token_types = [(name, re.compile(pattern)) for name, pattern in token_types]
    
    # Convert source string into a list of tokens
    def tokenize(self, contents):
        position = 0  # Current position in source string
        tokens = []   # List to store token tuples (type, value)
        while position < len(contents):
            match = None
            # Try matching each token type at current position
            for name, pattern in self.token_types:
                match = pattern.match(contents, position)
                if match:
                    value = match.group(0)
                    # Special handling for identifiers that are keywords
                    if name == 'IDENTIFIER' and value in self.keywords:
                        tokens.append(('KEYWORD', value))
                    elif name != 'WHITESPACE':  # Skip whitespace
                        tokens.append((name, value))
                    position = match.end()  # Move to end of matched token
                    break
            if not match:
                # Raise error with context if no token matches
                raise ValueError(f"Unable to match contents at position {position}: '{contents[position:position+10]}...'")
        return tokens  # Return list of tokens