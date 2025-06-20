class PythonSemanticAnalyzer:
    # Analyzes the AST and returns a list of semantic errors
    def analyze(self, ast):
        errors = []
        for statement in ast['statements']:
            if statement['type'] == 'PRINT_STATEMENT':
                if 'args' not in statement or not statement['args']:
                    errors.append("Print statement must have at least one argument to print.")
                else:
                    for arg in statement['args']:
                        if arg['type'] not in ['STRING_LITERAL', 'IDENTIFIER', 'BINARY_EXPRESSION', 'NUMBER', 'FUNCTION_CALL']:
                            errors.append(f"Print statement only supports string literals, identifiers, binary expressions, numbers, or function calls. Found: {arg['type']}")
            elif statement['type'] == 'ASSIGNMENT':
                if 'expression' not in statement:
                    errors.append(f"Assignment for variable '{statement['var_name']}' must have an expression.")
                else:
                    if not isinstance(statement['var_name'], str) or not statement['var_name']:
                        errors.append(f"Assignment must have a valid variable name, got: {statement['var_name']}")
                    expr = statement['expression']
                    if expr['type'] == 'FUNCTION_CALL' and expr['func_name'] not in ['input', 'int']:
                        errors.append(f"Unsupported function call '{expr['func_name']}' in assignment.")
            elif statement['type'] == 'FOR_LOOP':
                if 'iterator' not in statement or not statement['iterator']:
                    errors.append("For loop must have a valid iterator variable.")
                if 'limit' in statement:
                    if 'start' in statement or 'stop' in statement or 'step' in statement:
                        errors.append("For loop with 'limit' cannot have 'start', 'stop', or 'step'.")
                else:
                    if 'start' not in statement:
                        errors.append("For loop with multiple arguments must have a start value.")
                    if 'stop' not in statement:
                        errors.append("For loop with multiple arguments must have a stop value.")
                if 'body' not in statement:
                    errors.append("For loop must have a body.")
                else:
                    if not isinstance(statement['body'], list):
                        errors.append("For loop body must be a list of statements.")
                    else:
                        for stmt in statement['body']:
                            sub_errors = self.analyze({'statements': [stmt]})
                            errors.extend(sub_errors)
            elif statement['type'] == 'WHILE_LOOP':
                if 'condition' not in statement:
                    errors.append("While loop must have a condition.")
                if 'body' not in statement:
                    errors.append("While loop must have a body.")
                else:
                    if statement['condition']['type'] not in ['BINARY_EXPRESSION', 'IDENTIFIER', 'NUMBER', 'STRING_LITERAL', 'FUNCTION_CALL']:
                        errors.append(f"Invalid condition type in while loop: {statement['condition']['type']}")
                    if not isinstance(statement['body'], list):
                        errors.append("While loop body must be a list of statements.")
                    else:
                        for stmt in statement['body']:
                            sub_errors = self.analyze({'statements': [stmt]})
                            errors.extend(sub_errors)
            elif statement['type'] == 'IF_STATEMENT':
                if 'condition' not in statement:
                    errors.append("If statement must have a condition.")
                if 'true_branch' not in statement:
                    errors.append("If statement must have a true branch.")
                else:
                    if statement['condition']['type'] not in ['BINARY_EXPRESSION', 'IDENTIFIER', 'NUMBER', 'STRING_LITERAL', 'FUNCTION_CALL']:
                        errors.append(f"Invalid condition type in if statement: {statement['condition']['type']}")
                    # Handle BLOCK in true_branch
                    if statement['true_branch']['type'] == 'BLOCK':
                        sub_errors = self.analyze({'statements': statement['true_branch']['statements']})
                    else:
                        sub_errors = self.analyze({'statements': [statement['true_branch']]})
                    errors.extend(sub_errors)
                    # Handle BLOCK in false_branch
                    if statement.get('false_branch'):
                        if statement['false_branch']['type'] == 'BLOCK':
                            sub_errors = self.analyze({'statements': statement['false_branch']['statements']})
                        else:
                            sub_errors = self.analyze({'statements': [statement['false_branch']]})
                        errors.extend(sub_errors)
            elif statement['type'] == 'FUNCTION_CALL':
                if 'func_name' not in statement or 'args' not in statement:
                    errors.append("Function call must have a name and arguments.")
            elif statement['type'] == 'RETURN_STATEMENT':
                if 'expression' not in statement:
                    errors.append("Return statement must have an expression.")
            elif statement['type'] == 'VARIABLE_DECLARATION':
                if 'var_type' not in statement or 'var_name' not in statement:
                    errors.append("Variable declaration must have a type and name.")
                if statement.get('initializer') and statement['initializer']['type'] not in ['NUMBER', 'STRING_LITERAL', 'IDENTIFIER', 'BINARY_EXPRESSION', 'FUNCTION_CALL']:
                    errors.append(f"Variable initializer must be a valid expression, got: {statement['initializer']['type']}")
            elif statement['type'] == 'IO_STATEMENT':
                if 'io_operator' not in statement or 'expression' not in statement:
                    errors.append("IO statement must have an operator and expression.")
            elif statement['type'] == 'BLOCK':  # Add BLOCK handling
                sub_errors = self.analyze({'statements': statement['statements']})
                errors.extend(sub_errors)
            else:
                errors.append(f"Unsupported statement type: {statement['type']}")
        return errors