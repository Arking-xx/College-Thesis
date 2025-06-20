import json

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.position = 0
        self.statement_parser = StatementParser(self)
        self.expression_parser = ExpressionParser(self)

    def current_token(self):
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    def match(self, expected_type):
        token = self.current_token()
        if token and token[0] == expected_type:
            self.position += 1
            return token
        else:
            raise ValueError(f"Expected {expected_type} but got {token}")

    def parse_program(self):
        statements = []
        while self.current_token():
            if self.is_function_definition():
                statements.append(self.statement_parser.parse_function_definition())
            else:
                statements.append(self.statement_parser.parse_statement())
        return {'type': 'PROGRAM', 'statements': statements}

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


class StatementParser:
    def __init__(self, parser):
        self.parser = parser

    def parse_statement(self):
        token = self.parser.current_token()
        if not token:
            raise SyntaxError("Unexpected end of input while parsing statement")
        token_type, token_value = token
        if token_type == 'KEYWORD':
            if token_value == 'if':
                return self.parse_if_statement()
            elif token_value == 'while':
                return self.parse_while_loop()
            elif token_value == 'for':
                return self.parse_for_loop()
            elif token_value == 'return':
                return self.parse_return_statement()
            elif token_value in ['int', 'float', 'double', 'bool', 'char', 'string', 'void']:
                next_token = self.parser.tokens[self.parser.position + 1] if self.parser.position + 1 < len(self.parser.tokens) else None
                if next_token and next_token[0] == 'IDENTIFIER':
                    next_next_token = self.parser.tokens[self.parser.position + 2] if self.parser.position + 2 < len(self.parser.tokens) else None
                    if next_next_token and next_next_token[0] == 'LPAREN':
                        return self.parse_function_definition()
                    else:
                        return self.parse_variable_declaration()
                else:
                    raise SyntaxError(f"Expected identifier after type '{token_value}'")
            else:
                raise SyntaxError(f"Unsupported keyword: {token_value}")
        elif token_type == 'IDENTIFIER':
            next_token = self.parser.tokens[self.parser.position + 1] if self.parser.position + 1 < len(self.parser.tokens) else None
            if next_token and next_token[0] == 'LPAREN':
                return self.parse_function_call()
            elif next_token and next_token[0] == 'ARITHMETIC_OPERATOR' and next_token[1] in ['++', '--']:
                return self.parse_expression_statement()
            elif next_token and next_token[0] in ['ARITHMETIC_OPERATOR', 'COMPOUND_ASSIGNMENT'] and next_token[1] not in ['++', '--']:
                return self.parse_assignment()
            elif token_value in ['cout', 'cin']:
                return self.parse_io_statement()
            else:
                return self.parse_expression_statement()
        elif token_type == 'NUMBER':
            return self.parse_expression_statement()
        elif token_type == 'LBRACE':
            return self.parse_block()
        elif token_type == 'SEMICOLON':
            self.parser.match('SEMICOLON')
            return {'type': 'EMPTY_STATEMENT'}
        else:
            raise SyntaxError(f"Unexpected token: {token_type} {token_value}")

    def parse_function_definition(self):
        return_type = self.parser.match('KEYWORD')[1]
        func_name = self.parser.match('IDENTIFIER')[1]
        self.parser.match('LPAREN')
        self.parser.match('RPAREN')
        body = self.parse_block()
        return {
            'type': 'FUNCTION_DEFINITION',
            'return_type': return_type,
            'func_name': func_name,
            'body': body['statements']
        }

    def parse_assignment(self):
        var_name = self.parser.match('IDENTIFIER')[1]
        next_token = self.parser.current_token()
        if next_token and next_token[0] == 'ARITHMETIC_OPERATOR' and next_token[1] == '=':
            self.parser.match('ARITHMETIC_OPERATOR')
            expression = self.parser.expression_parser.parse_expression()
            self.parser.match('SEMICOLON')
            return {'type': 'ASSIGNMENT', 'var_name': var_name, 'expression': expression}
        elif next_token and next_token[0] == 'COMPOUND_ASSIGNMENT':
            operator = self.parser.match('COMPOUND_ASSIGNMENT')[1]
            right_expr = self.parser.expression_parser.parse_expression()
            self.parser.match('SEMICOLON')
            return {
                'type': 'ASSIGNMENT',
                'var_name': var_name,
                'expression': {
                    'type': 'BINARY_EXPRESSION',
                    'operator': operator[0],
                    'left': {'type': 'IDENTIFIER', 'value': var_name},
                    'right': right_expr
                }
            }
        else:
            raise SyntaxError(f"Expected '=' or compound assignment operator after identifier '{var_name}' in assignment")

    def parse_expression_statement(self):
        expression = self.parser.expression_parser.parse_expression()
        self.parser.match('SEMICOLON')
        return {'type': 'EXPRESSION_STATEMENT', 'expression': expression}

    def parse_while_loop(self):
        self.parser.match('KEYWORD')
        self.parser.match('LPAREN')
        condition = self.parser.expression_parser.parse_expression()
        self.parser.match('RPAREN')
        body = self.parse_statement()
        return {
            'type': 'WHILE_LOOP',
            'condition': condition,
            'body': body
        }

    def parse_for_loop(self):
        self.parser.match('KEYWORD')  # 'for'
        self.parser.match('LPAREN')
        init = None
        if self.parser.current_token()[0] == 'KEYWORD':
            init_type = self.parser.match('KEYWORD')[1]
            var_name = self.parser.match('IDENTIFIER')[1]
            self.parser.match('ARITHMETIC_OPERATOR')  # Expect '='
            start_value = self.parser.expression_parser.parse_expression()
            init = {'type': 'VARIABLE_DECLARATION', 'var_type': init_type, 'var_name': var_name, 'initializer': start_value}
        elif self.parser.current_token()[0] == 'IDENTIFIER':
            var_name = self.parser.match('IDENTIFIER')[1]
            self.parser.match('ARITHMETIC_OPERATOR')  # Expect '='
            start_value = self.parser.expression_parser.parse_expression()
            init = {'type': 'ASSIGNMENT', 'var_name': var_name, 'expression': start_value}
        else:
            raise SyntaxError("For loop initialization must start with a type or identifier")
        self.parser.match('SEMICOLON')
        condition = None
        if self.parser.current_token()[0] != 'SEMICOLON':
            condition = self.parser.expression_parser.parse_expression()
        else:
            condition = {'type': 'BOOLEAN_LITERAL', 'value': 'true'}
        self.parser.match('SEMICOLON')
        increment = None
        if self.parser.current_token()[0] != 'RPAREN':
            if self.parser.current_token()[0] == 'IDENTIFIER':
                inc_var = self.parser.match('IDENTIFIER')[1]
                next_token = self.parser.current_token()
                if next_token[0] == 'ARITHMETIC_OPERATOR' and next_token[1] in ['++', '--']:
                    operator = self.parser.match('ARITHMETIC_OPERATOR')[1]
                    increment = {'type': 'INCREMENT', 'var_name': inc_var, 'operator': operator}
                elif next_token[0] == 'ARITHMETIC_OPERATOR' and next_token[1] == '=':
                    self.parser.match('ARITHMETIC_OPERATOR')
                    expression = self.parser.expression_parser.parse_expression()
                    increment = {'type': 'ASSIGNMENT', 'var_name': inc_var, 'expression': expression}
                elif next_token[0] == 'COMPOUND_ASSIGNMENT':
                    operator = self.parser.match('COMPOUND_ASSIGNMENT')[1]
                    expression = self.parser.expression_parser.parse_expression()
                    increment = {
                        'type': 'ASSIGNMENT',
                        'var_name': inc_var,
                        'expression': {
                            'type': 'BINARY_EXPRESSION',
                            'operator': operator[0],
                            'left': {'type': 'IDENTIFIER', 'value': inc_var},
                            'right': expression
                        }
                    }
                else:
                    raise SyntaxError(f"Unexpected token after increment variable: {next_token}")
        self.parser.match('RPAREN')
        body = self.parse_statement()
        return {
            'type': 'FOR_LOOP',
            'init': init,
            'condition': condition,
            'increment': increment,
            'body': body
        }

    def parse_if_statement(self):
        self.parser.match('KEYWORD')
        self.parser.match('LPAREN')
        condition = self.parser.expression_parser.parse_expression()
        self.parser.match('RPAREN')
        true_branch = self.parse_statement()
        false_branch = None
        if self.parser.current_token() and self.parser.current_token()[1] == 'else':
            self.parser.match('KEYWORD')
            if self.parser.current_token() and self.parser.current_token()[0] == 'KEYWORD' and self.parser.current_token()[1] == 'if':
                false_branch = self.parse_if_statement()
            else:
                false_branch = self.parse_statement()
        return {
            'type': 'IF_STATEMENT',
            'condition': condition,
            'true_branch': true_branch,
            'false_branch': false_branch
        }

    def parse_block(self):
        self.parser.match('LBRACE')
        statements = []
        while self.parser.current_token() and self.parser.current_token()[0] != 'RBRACE':
            statements.append(self.parse_statement())
        self.parser.match('RBRACE')
        return {'type': 'BLOCK', 'statements': statements}

    def parse_io_statement(self):
        io_operator = self.parser.match('IDENTIFIER')[1]
        expressions = []
        while self.parser.current_token() and self.parser.current_token()[0] == 'INSERTION_OPERATOR':
            self.parser.match('INSERTION_OPERATOR')
            if self.parser.current_token()[0] in ['STRING', 'IDENTIFIER', 'NUMBER', 'LPAREN']:
                expression = self.parser.expression_parser.parse_expression()
                expressions.append(expression)
            else:
                raise SyntaxError(f"Expected expression after '{io_operator} <<'")
        self.parser.match('SEMICOLON')
        return {
            'type': 'IO_STATEMENT',
            'io_operator': io_operator,
            'expressions': expressions
        }

    def parse_return_statement(self):
        self.parser.match('KEYWORD')
        expression = self.parser.expression_parser.parse_expression()
        self.parser.match('SEMICOLON')
        return {
            'type': 'RETURN_STATEMENT',
            'expression': expression
        }

    def parse_variable_declaration(self):
        if self.parser.current_token()[1] in ['int', 'float', 'double', 'bool', 'char', 'string', 'void']:
            var_type = self.parser.match('KEYWORD')[1]
            var_name = self.parser.match('IDENTIFIER')[1]
            if self.parser.current_token() and self.parser.current_token()[0] == 'ARITHMETIC_OPERATOR' and self.parser.current_token()[1] == '=':
                self.parser.match('ARITHMETIC_OPERATOR')
                initializer = self.parser.expression_parser.parse_expression()
                self.parser.match('SEMICOLON')
                return {'type': 'VARIABLE_DECLARATION', 'var_type': var_type, 'var_name': var_name, 'initializer': initializer}
            else:
                self.parser.match('SEMICOLON')
                return {'type': 'VARIABLE_DECLARATION', 'var_type': var_type, 'var_name': var_name}
        else:
            raise SyntaxError(f"Unsupported type: {self.parser.current_token()[1]}")

    def parse_function_call(self):
        func_name = self.parser.match('IDENTIFIER')[1]
        self.parser.match('LPAREN')
        args = []
        if self.parser.current_token()[0] != 'RPAREN':
            args.append(self.parser.expression_parser.parse_expression())
            while self.parser.current_token() and self.parser.current_token()[0] == 'COMMA':
                self.parser.match('COMMA')
                args.append(self.parser.expression_parser.parse_expression())
        self.parser.match('RPAREN')
        self.parser.match('SEMICOLON')
        return {'type': 'FUNCTION_CALL', 'func_name': func_name, 'args': args}


class ExpressionParser:
    def __init__(self, parser):
        self.parser = parser

    def parse_expression(self):
        left = self.parse_term()
        while self.parser.current_token() and self.parser.current_token()[0] in ['ARITHMETIC_OPERATOR', 'RELATIONAL_OPERATOR']:
            operator = self.parser.match(self.parser.current_token()[0])[1]
            right = self.parse_term()
            left = {'type': 'BINARY_EXPRESSION', 'operator': operator, 'left': left, 'right': right}
        return left

    def parse_term(self):
        token = self.parser.current_token()
        if token[0] == 'NUMBER':
            return {'type': 'NUMBER', 'value': self.parser.match('NUMBER')[1]}
        elif token[0] == 'IDENTIFIER':
            node = {'type': 'IDENTIFIER', 'value': self.parser.match('IDENTIFIER')[1]}
            if self.parser.current_token() and self.parser.current_token()[0] == 'ARITHMETIC_OPERATOR' and self.parser.current_token()[1] in ['++', '--']:
                operator = self.parser.match('ARITHMETIC_OPERATOR')[1]
                return {'type': 'INCREMENT', 'var_name': node['value'], 'operator': operator}
            return node
        elif token[0] == 'STRING':
            return {'type': 'STRING_LITERAL', 'value': self.parser.match('STRING')[1]}
        elif token[0] == 'LPAREN':
            self.parser.match('LPAREN')
            expression = self.parse_expression()
            self.parser.match('RPAREN')
            return expression
        else:
            if token[0] in ['SEMICOLON', 'LBRACE', 'RBRACE']:
                raise SyntaxError(f"Unexpected end of expression: {token}")
            raise SyntaxError(f"Unexpected token in expression: {token}")