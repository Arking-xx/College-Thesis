import re

# Main parser class to convert token stream into an AST
class PythonParser:
    def __init__(self, tokens):
        self.tokens = tokens  # List of token tuples (type, value)
        self.position = 0     # Current position in token stream
        self.statement_parser = StatementParser(self)  # Helper for statements
        self.expression_parser = ExpressionParser(self)  # Helper for expressions

    # Get current token or None if at end
    def current_token(self):
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    # Match and consume expected token type, raise error if mismatch
    def match(self, expected_type):
        token = self.current_token()
        if token and token[0] == expected_type:
            self.position += 1
            return token
        else:
            raise ValueError(f"Expected {expected_type} but got {token}")

    # Check if current tokens indicate a function definition
    def is_function_definition(self):
        if (
            self.current_token()
            and self.current_token()[0] == 'KEYWORD'
            and self.current_token()[1] in ['int', 'float', 'void']
        ):
            next_token = self.tokens[self.position + 1] if self.position + 1 < len(self.tokens) else None
            if next_token and next_token[0] == 'IDENTIFIER':
                next_next_token = self.tokens[self.position + 2] if self.position + 2 < len(self.tokens) else None
                if next_next_token and next_next_token[0] == 'LPAREN':
                    return True
        return False

    # Parse entire token stream into a PROGRAM AST node
    def parse_program(self):
        statements = []
        while self.current_token():
            if self.is_function_definition():
                statements.append(self.statement_parser.parse_function_definition())
            else:
                statements.append(self.statement_parser.parse_statement())
        return {'type': 'PROGRAM', 'statements': statements}

# Helper class to parse statements
class StatementParser:
    def __init__(self, parser):
        self.parser = parser  # Reference to main parser

    # Parse a single statement based on current token
    def parse_statement(self):
        token = self.parser.current_token()
        if not token:
            raise SyntaxError("Unexpected end of input while parsing statement")
        token_type, token_value = token
        if token_type == 'KEYWORD':
            if token_value == 'print':
                return self.parse_print_statement()
            elif token_value == 'if':
                return self.parse_if_statement()
            elif token_value == 'while':
                return self.parse_while_loop()
            elif token_value == 'return':
                return self.parse_return_statement()
            elif token_value == 'for':
                return self.parse_for_loop()
            elif token_value in ['int', 'float', 'void']:
                next_token = self.parser.tokens[self.parser.position + 1] if self.parser.position + 1 < len(self.parser.tokens) else None
                if next_token and next_token[0] == 'IDENTIFIER':
                    next_next_token = self.parser.tokens[self.parser.position + 2] if self.parser.position + 2 < len(self.parser.tokens) else None
                    if next_next_token and next_next_token[0] == 'LPAREN':
                        return self.parse_function_definition()
                    else:
                        return self.parse_variable_declaration()
                else:
                    raise SyntaxError(f"Unexpected token after type: {token_value}")
            elif token_value in ['elif', 'else']:
                raise SyntaxError(f"'{token_value}' encountered outside of if statement context")
            else:
                raise SyntaxError(f"Unsupported keyword: {token_value}")
        elif token_type == 'IDENTIFIER':
            next_token = self.parser.tokens[self.parser.position + 1] if self.parser.position + 1 < len(self.parser.tokens) else None
            if next_token and next_token[0] == 'LPAREN':
                return self.parse_function_call()
            elif next_token and (next_token[0] == 'ASSIGNMENT_OPERATOR' or 
                                (next_token[0] == 'ARITHMETIC_OPERATOR' and 
                                self.parser.tokens[self.parser.position + 2][0] == 'ASSIGNMENT_OPERATOR' if self.parser.position + 2 < len(self.parser.tokens) else False)):
                return self.parse_assignment()
            elif token_value in ['cout', 'cin']:
                return self.parse_io_statement()
            else:
                raise SyntaxError(f"Unexpected identifier usage: {token_value}")
        elif token_type == 'LBRACE':
            return self.parse_block()
        else:
            raise SyntaxError(f"Unexpected token: {token_type} {token_value}")

    # Parse function definition (e.g., int foo())
    def parse_function_definition(self):
        return_type = self.parser.match('KEYWORD')[1]  # e.g., 'int'
        func_name = self.parser.match('IDENTIFIER')[1]  # Function name
        self.parser.match('LPAREN')
        self.parser.match('RPAREN')  # No parameters supported yet
        body = self.parse_block()
        return {
            'type': 'FUNCTION_DEFINITION',
            'return_type': return_type,
            'func_name': func_name,
            'body': body['statements'],
        }

    # Parse for loop (e.g., for i in range(...))
    def parse_for_loop(self):
        self.parser.match('KEYWORD')  # 'for'
        iterator = self.parser.match('IDENTIFIER')[1]  # Loop variable
        self.parser.match('IDENTIFIER')  # 'in'
        range_token = self.parser.match('IDENTIFIER')
        if range_token[1] != 'range':
            raise SyntaxError("Expected 'range' after 'in' in for loop")
        self.parser.match('LPAREN')
        start = self.parser.expression_parser.parse_expression()  # First range arg
        stop = None
        step = None
        if self.parser.current_token() and self.parser.current_token()[0] == 'COMMA':
            self.parser.match('COMMA')
            stop = self.parser.expression_parser.parse_expression()  # Second range arg
            if self.parser.current_token() and self.parser.current_token()[0] == 'COMMA':
                self.parser.match('COMMA')
                step = self.parser.expression_parser.parse_expression()  # Third range arg
        self.parser.match('RPAREN')
        self.parser.match('COLON')
        body = [self.parse_statement()]  # Single statement body
        if stop is None:
            return {'type': 'FOR_LOOP', 'iterator': iterator, 'limit': start, 'body': body}
        elif step is None:
            return {'type': 'FOR_LOOP', 'iterator': iterator, 'start': start, 'stop': stop, 'body': body}
        else:
            return {'type': 'FOR_LOOP', 'iterator': iterator, 'start': start, 'stop': stop, 'step': step, 'body': body}

    # Parse while loop
    def parse_while_loop(self):
        self.parser.match('KEYWORD')  # 'while'
        condition = self.parser.expression_parser.parse_expression()
        self.parser.match('COLON')    # Expect ':'
        body = []
        while self.parser.current_token() and self.parser.current_token()[1] not in ['while', 'for']:
            body.append(self.parse_statement())
        return {'type': 'WHILE_LOOP', 'condition': condition, 'body': body}

    # Parse variable declaration (e.g., int x = 5)
    def parse_variable_declaration(self):
        var_type = self.parser.match('KEYWORD')[1]  # e.g., 'int'
        var_name = self.parser.match('IDENTIFIER')[1]
        if self.parser.current_token() and self.parser.current_token()[0] == 'ASSIGNMENT_OPERATOR':
            self.parser.match('ASSIGNMENT_OPERATOR')
            initializer = self.parser.expression_parser.parse_expression()
            if self.parser.current_token() and self.parser.current_token()[0] == 'SEMICOLON':
                self.parser.match('SEMICOLON')
            return {'type': 'VARIABLE_DECLARATION', 'var_type': var_type, 'var_name': var_name, 'initializer': initializer}
        else:
            if self.parser.current_token() and self.parser.current_token()[0] == 'SEMICOLON':
                self.parser.match('SEMICOLON')
            return {'type': 'VARIABLE_DECLARATION', 'var_type': var_type, 'var_name': var_name}

    # Parse assignment (e.g., x = 5 or x += 1)
    def parse_assignment(self):
        var_name = self.parser.match('IDENTIFIER')[1]
        next_token = self.parser.current_token()
        if next_token[0] == 'ASSIGNMENT_OPERATOR':
            self.parser.match('ASSIGNMENT_OPERATOR')
            expression = self.parser.expression_parser.parse_expression()
        elif next_token[0] == 'ARITHMETIC_OPERATOR':
            operator = self.parser.match('ARITHMETIC_OPERATOR')[1]
            self.parser.match('ASSIGNMENT_OPERATOR')
            right = self.parser.expression_parser.parse_expression()
            expression = {
                'type': 'BINARY_EXPRESSION',
                'operator': operator,
                'left': {'type': 'IDENTIFIER', 'value': var_name},
                'right': right
            }
        else:
            raise SyntaxError(f"Expected assignment operator after {var_name}")
        if self.parser.current_token() and self.parser.current_token()[0] == 'SEMICOLON':
            self.parser.match('SEMICOLON')
        return {'type': 'ASSIGNMENT', 'var_name': var_name, 'expression': expression}

    # Parse function call (e.g., foo())
    def parse_function_call(self):
        func_name = self.parser.match('IDENTIFIER')[1]
        self.parser.match('LPAREN')
        args = self.parse_arguments()
        self.parser.match('RPAREN')
        if self.parser.current_token() and self.parser.current_token()[0] == 'SEMICOLON':
            self.parser.match('SEMICOLON')
        return {'type': 'FUNCTION_CALL', 'func_name': func_name, 'args': args}

    # Parse comma-separated arguments
    def parse_arguments(self):
        args = []
        while self.parser.current_token() and self.parser.current_token()[0] != 'RPAREN':
            args.append(self.parser.expression_parser.parse_expression())
            if self.parser.current_token() and self.parser.current_token()[0] == 'COMMA':
                self.parser.match('COMMA')
        return args

    # Parse if statement with optional elif/else
    def parse_if_statement(self):
        self.parser.match('KEYWORD')  # 'if'
        condition = self.parser.expression_parser.parse_expression()
        self.parser.match('COLON')    # Expect ':'
        true_body = []
        if self.parser.current_token():
            true_body.append(self.parse_statement())  # Single statement for true branch
        true_branch = {'type': 'BLOCK', 'statements': true_body}
        false_branch = None
        current_node = None

        while self.parser.current_token() and self.parser.current_token()[1] in ['elif', 'else']:
            if self.parser.current_token()[1] == 'elif':
                self.parser.match('KEYWORD')  # 'elif'
                elif_condition = self.parser.expression_parser.parse_expression()
                self.parser.match('COLON')
                elif_body = []
                if self.parser.current_token():
                    elif_body.append(self.parse_statement())  # Single statement for elif
                elif_true_branch = {'type': 'BLOCK', 'statements': elif_body}
                elif_node = {
                    'type': 'IF_STATEMENT',
                    'condition': elif_condition,
                    'true_branch': elif_true_branch,
                    'false_branch': None
                }
                if not false_branch:
                    false_branch = elif_node
                    current_node = elif_node
                else:
                    current_node['false_branch'] = elif_node
                    current_node = elif_node
            elif self.parser.current_token()[1] == 'else':
                self.parser.match('KEYWORD')  # 'else'
                self.parser.match('COLON')
                else_body = []
                if self.parser.current_token():
                    else_body.append(self.parse_statement())  # Single statement for else
                else_block = {'type': 'BLOCK', 'statements': else_body}
                if not false_branch:
                    false_branch = else_block
                else:
                    current_node['false_branch'] = else_block
                break
        return {
            'type': 'IF_STATEMENT',
            'condition': condition,
            'true_branch': true_branch,
            'false_branch': false_branch
        }

    # Parse C++-style I/O (e.g., cout << x)
    def parse_io_statement(self):
        io_operator = self.parser.match('IDENTIFIER')[1]  # 'cout' or 'cin'
        operator_token = self.parser.current_token()
        if operator_token and operator_token[0] == 'INSERTION_OPERATOR':
            self.parser.match('INSERTION_OPERATOR')
            expression = self.parser.expression_parser.parse_expression()
            self.parser.match('SEMICOLON')
            return {
                'type': 'IO_STATEMENT',
                'io_operator': io_operator,
                'expression': expression
            }
        else:
            raise SyntaxError(f"Expected insertion operator after {io_operator}")

    # Parse print statement
    def parse_print_statement(self):
        self.parser.match('KEYWORD')  # 'print'
        self.parser.match('LPAREN')
        args = []
        while self.parser.current_token() and self.parser.current_token()[0] != 'RPAREN':
            args.append(self.parser.expression_parser.parse_expression())
            if self.parser.current_token() and self.parser.current_token()[0] == 'COMMA':
                self.parser.match('COMMA')
        self.parser.match('RPAREN')
        return {'type': 'PRINT_STATEMENT', 'args': args}

    # Parse block (e.g., { ... })
    def parse_block(self):
        self.parser.match('LBRACE')
        statements = []
        while self.parser.current_token() and self.parser.current_token()[0] != 'RBRACE':
            statements.append(self.parse_statement())
        self.parser.match('RBRACE')
        return {'type': 'BLOCK', 'statements': statements}

    # Placeholder for return statement (not implemented)
    def parse_return_statement(self):
        raise NotImplementedError("Return statement parsing not implemented")

# Helper class to parse expressions
class ExpressionParser:
    def __init__(self, parser):
        self.parser = parser  # Reference to main parser

    # Parse expressions with binary operators
    def parse_expression(self):
        left = self.parse_term()
        while self.parser.current_token() and self.parser.current_token()[0] in ['ARITHMETIC_OPERATOR', 'RELATIONAL_OPERATOR', 'COMPARISON_OPERATOR']:
            operator = self.parser.match(self.parser.current_token()[0])[1]
            right = self.parse_term()
            left = {'type': 'BINARY_EXPRESSION', 'operator': operator, 'left': left, 'right': right}
        return left

    # Parse basic terms (numbers, strings, identifiers, function calls)
    def parse_term(self):
        token = self.parser.current_token()
        if not token:
            raise SyntaxError("Unexpected end of input in expression")
        if token[0] == 'NUMBER':
            return {'type': 'NUMBER', 'value': self.parser.match('NUMBER')[1]}
        elif token[0] == 'STRING':
            return {'type': 'STRING_LITERAL', 'value': self.parser.match('STRING')[1]}
        elif token[0] in ['IDENTIFIER', 'KEYWORD']:
            token_type, token_value = token
            self.parser.match(token_type)
            if self.parser.current_token() and self.parser.current_token()[0] == 'LPAREN':
                self.parser.match('LPAREN')
                args = self.parse_arguments()
                self.parser.match('RPAREN')
                return {'type': 'FUNCTION_CALL', 'func_name': token_value, 'args': args}
            if token_type == 'IDENTIFIER':
                return {'type': 'IDENTIFIER', 'value': token_value}
            else:
                raise SyntaxError(f"Keyword '{token_value}' used outside of function call")
        elif token[0] == 'LPAREN':
            self.parser.match('LPAREN')
            expression = self.parse_expression()
            self.parser.match('RPAREN')
            return expression
        else:
            raise SyntaxError(f"Unexpected token in expression: {token}")

    # Parse comma-separated arguments for function calls
    def parse_arguments(self):
        args = []
        while self.parser.current_token() and self.parser.current_token()[0] != 'RPAREN':
            args.append(self.parse_expression())
            if self.parser.current_token() and self.parser.current_token()[0] == 'COMMA':
                self.parser.match('COMMA')
        return args