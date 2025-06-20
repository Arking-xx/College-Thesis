# Manages semantic analysis of an abstract syntax tree (AST) by tracking scopes and variables
class SemanticAnalyzer:
    def __init__(self):
        self.scope_stack = [{}]  # Stack of scopes, starting with global scope
        self.current_class = None  # Tracks current class context for methods

    # Retrieves the innermost scope from the scope stack
    def current_scope(self):
        return self.scope_stack[-1]

    # Creates a new scope and adds it to the scope stack
    def enter_scope(self):
        self.scope_stack.append({})

    # Removes the current scope from the scope stack
    def exit_scope(self):
        self.scope_stack.pop()

    # Adds a variable to the current scope, checking for redeclarations or shadowing
    def declare_variable(self, var_name, var_type, errors, is_member=False):
        scope = self.current_scope()
        if var_name in scope:
            errors.append(f"Error: Variable '{var_name}' already declared in this scope.")
        elif self.lookup_variable(var_name) is not None and not is_member:
            errors.append(f"Warning: Variable '{var_name}' shadows a declaration in an outer scope.")
        else:
            scope[var_name] = var_type

    # Searches for a variable in all scopes, from innermost to outermost
    def lookup_variable(self, var_name):
        for scope in reversed(self.scope_stack):
            if var_name in scope:
                return scope[var_name]
        return None

    # Performs semantic analysis on the entire AST and collects errors
    def analyze(self, ast):
        errors = []
        if ast['type'] != 'PROGRAM':
            errors.append("Expected AST root to be of type 'PROGRAM'")
            return errors
        for statement in ast['statements']:
            self.analyze_statement(statement, errors)
        return errors

    # Processes a single statement in the AST and updates the error list
    def analyze_statement(self, statement, errors):
        handlers = {
            'VARIABLE_DECLARATION': self._analyze_variable_declaration,
            'ASSIGNMENT': self.check_assignment,
            'FUNCTION_DEFINITION': self.analyze_function,
            'BLOCK': self.analyze_block,
            'IF_STATEMENT': self.analyze_if_statement,
            'WHILE_LOOP': self.analyze_while_loop,
            'RETURN_STATEMENT': self.analyze_return_statement,
            'CLASS_DEFINITION': self.analyze_class_definition,
            'IO_STATEMENT': self.analyze_io_statement,
            'INCREMENT': self.analyze_increment,
            'FOR_LOOP': self.analyze_for_loop,
            'EXPRESSION_STATEMENT': self.analyze_expression_statement,
        }
        handler = handlers.get(statement['type'])
        if handler:
            handler(statement, errors)
        else:
            errors.append(f"Warning: Unsupported statement type '{statement['type']}'.")

    # Validates an increment operation on a variable
    def analyze_increment(self, increment, errors):
        var_name = increment['var_name']
        var_type = self.lookup_variable(var_name)
        if var_type is None:
            errors.append(f"Error: Variable '{var_name}' not declared for increment operation.")
        elif var_type not in ['int', 'float']:
            errors.append(f"Warning: Increment operation on non-numeric type '{var_type}' for variable '{var_name}'.")

    # Checks the semantics of an expression used as a standalone statement
    def analyze_expression_statement(self, statement, errors):
        if 'expression' in statement:
            expression = statement['expression']
            if expression['type'] == 'INCREMENT':
                var_type = self.lookup_variable(expression['var_name'])
                if var_type is None:
                    errors.append(f"Error: Variable '{expression['var_name']}' not declared for increment.")
                elif var_type not in ['int', 'float']:
                    errors.append(f"Warning: Increment operation on non-numeric type '{var_type}' for variable '{expression['var_name']}'.")
            else:
                self.evaluate_expression_type(expression, errors, "expression statement")
        else:
            errors.append("Expression statement must have an 'expression' field.")

    # Analyzes a block of statements within its own scope
    def analyze_block(self, block, errors):
        if not isinstance(block, dict) or 'statements' not in block:
            errors.append("Invalid block structure. Expected a dictionary with 'statements' key.")
            return
        self.enter_scope()
        for statement in block['statements']:
            self.analyze_statement(statement, errors)
        self.exit_scope()

    # Validates a function definition and its body
    def analyze_function(self, function, errors):
        if 'func_name' not in function or 'body' not in function:
            errors.append("Function definition must include 'func_name' and 'body' fields.")
            return
        func_name = function['func_name']
        params = function.get('params', [])
        for param in params:
            if 'name' not in param or 'type' not in param:
                errors.append("Function parameter must have 'name' and 'type' fields.")
        if func_name in self.scope_stack[0]:
            errors.append(f"Error: Function '{func_name}' already declared.")
        else:
            self.scope_stack[0][func_name] = {
                'type': 'function',
                'params': {param['name']: param['type'] for param in params},
                'return_type': function.get('return_type', 'void')
            }
        self.enter_scope()
        for param in params:
            self.declare_variable(param['name'], param['type'], errors)
        if isinstance(function['body'], list):
            self.analyze_block({'statements': function['body']}, errors)
        elif isinstance(function['body'], dict) and 'statements' in function['body']:
            self.analyze_block(function['body'], errors)
        else:
            errors.append("Invalid function body structure. Expected a list or dictionary with 'statements' key.")
        self.exit_scope()

    # Analyzes a variable declaration and checks type compatibility
    def _analyze_variable_declaration(self, declaration, errors):
        if 'var_name' not in declaration or 'var_type' not in declaration:
            errors.append("Variable declaration must have 'var_name' and 'var_type' fields.")
            return
        var_name = declaration['var_name']
        var_type = declaration['var_type']
        if self.lookup_variable(var_name):
            errors.append(f"Error: Variable '{var_name}' already declared.")
        else:
            self.declare_variable(var_name, var_type, errors)
        if 'initializer' in declaration:
            init_type = self.evaluate_expression_type(declaration['initializer'], errors, f"initializer for '{var_name}'")
            if init_type and not self._is_type_compatible(var_type, init_type):
                errors.append(f"Error: Type mismatch in variable declaration: '{var_name}' declared as '{var_type}' but initialized with type '{init_type}'.")

    # Checks type compatibility between declared type and expression type
    def _is_type_compatible(self, declared_type, expr_type):
        if declared_type == expr_type:
            return True
        if declared_type in ['int', 'float'] and expr_type in ['int', 'float']:
            return True
        if declared_type == 'string' and expr_type == 'string':
            return True
        return False

    # Ensures type correctness in assignment statements
    def check_assignment(self, statement, errors):
        if 'var_name' not in statement or 'expression' not in statement:
            errors.append("Assignment statement must have 'var_name' and 'expression' fields.")
            return
        var_name = statement['var_name']
        expression = statement['expression']
        var_type = self.lookup_variable(var_name)
        if var_type is None:
            errors.append(f"Error: Variable '{var_name}' not declared.")
            return
        expr_type = self.evaluate_expression_type(expression, errors, f"assignment to '{var_name}'")
        if expr_type and var_type != expr_type:
            errors.append(f"Error: Type mismatch in assignment to '{var_name}'. Expected {var_type}, got {expr_type}.")

    # Validates the structure and semantics of an if statement
    def analyze_if_statement(self, statement, errors):
        if 'condition' not in statement or 'true_branch' not in statement:
            errors.append("If statement must have 'condition' and 'true_branch' fields.")
            return
        condition_type = self.evaluate_expression_type(statement['condition'], errors, "if statement condition")
        if condition_type != 'bool':
            errors.append(f"Error: Condition in if statement must be of type 'bool', got {condition_type}.")
        self.analyze_statement(statement['true_branch'], errors)
        if 'false_branch' in statement and statement['false_branch'] is not None:
            self.analyze_statement(statement['false_branch'], errors)

    # Checks the semantics of a while loop, including its condition and body
    def analyze_while_loop(self, while_loop, errors):
        if 'condition' not in while_loop or 'body' not in while_loop:
            errors.append("While loop must have 'condition' and 'body' fields.")
            return
        condition_type = self.evaluate_expression_type(while_loop['condition'], errors, "while loop condition")
        if condition_type != 'bool':
            errors.append(f"Error: Condition in while loop must be of type 'bool', got {condition_type}.")
        if while_loop['body'] is not None:
            self.analyze_statement(while_loop['body'], errors)
        else:
            errors.append("Error: While loop body is None.")

    # Verifies the semantics of a return statement
    def analyze_return_statement(self, statement, errors):
        if 'expression' not in statement:
            errors.append("Return statement must have an 'expression' field.")
            return
        expression_type = self.evaluate_expression_type(statement['expression'], errors, "return statement")
        if expression_type is None:
            errors.append("Error: Invalid expression in return statement.")

    # Analyzes input/output statements for correctness
    def analyze_io_statement(self, statement, errors):
        if 'io_operator' not in statement:
            errors.append("I/O statement must have an 'io_operator' field.")
            return
        if 'expressions' not in statement:
            errors.append("I/O statement must have an 'expressions' field.")
            return
        for expression in statement.get('expressions', []):
            expr_type = self.evaluate_expression_type(expression, errors, f"I/O statement with operator '{statement['io_operator']}'")
            if expr_type is None:
                errors.append(f"Error: Invalid expression in I/O statement.")

    # Determines the type of an expression in the AST
    def evaluate_expression_type(self, expression, errors=None, context="expression"):
        if errors is None:
            errors = []  # Fallback for cases where errors aren't passed
        if expression['type'] == 'NUMBER':
            return 'int'
        elif expression['type'] == 'IDENTIFIER':
            var_type = self.lookup_variable(expression['value'])
            if var_type is None:
                errors.append(f"Error: Variable '{expression['value']}' not declared in {context}.")
            return var_type
        elif expression['type'] == 'BINARY_EXPRESSION':
            left_type = self.evaluate_expression_type(expression['left'], errors, f"left operand of '{expression['operator']}' in {context}")
            right_type = self.evaluate_expression_type(expression['right'], errors, f"right operand of '{expression['operator']}' in {context}")
            operator = expression['operator']
            if operator in ['>', '<', '>=', '<=', '==', '!=']:
                if left_type and right_type:
                    if left_type == right_type:
                        return 'bool'
                    else:
                        errors.append(f"Error: Type mismatch in {context} for operator '{operator}'. Cannot compare '{left_type}' with '{right_type}'.")
                        return None
                else:
                    return None
            else:
                if left_type == 'float' or right_type == 'float':
                    return 'float'
                elif left_type == 'int' and right_type == 'int':
                    return 'int'
                else:
                    errors.append(f"Error: Invalid types '{left_type}' and '{right_type}' for operator '{operator}' in {context}.")
                    return None
        elif expression['type'] == 'STRING_LITERAL':
            return 'string'
        elif expression['type'] == 'FUNCTION_CALL':
            func_name = expression['func_name']
            func_info = self.lookup_variable(func_name)
            if func_info and func_info['type'] == 'function':
                return func_info.get('return_type', 'void')
            else:
                errors.append(f"Error: Function '{func_name}' not declared in {context}.")
                return None
        elif expression['type'] == 'BOOLEAN_LITERAL':
            return 'bool'
        else:
            errors.append(f"Error: Unsupported expression type '{expression['type']}' in {context}.")
            return None

    # Analyzes a class definition and its members
    def analyze_class_definition(self, class_def, errors):
        if 'class_name' not in class_def or 'body' not in class_def:
            errors.append("Class definition must have 'class_name' and 'body' fields.")
            return
        class_name = class_def['class_name']
        if class_name in self.scope_stack[0]:
            errors.append(f"Error: Class '{class_name}' already declared.")
            return
        self.scope_stack[0][class_name] = {
            'type': 'class',
            'members': {}
        }
        self.current_class = class_name
        self.enter_scope()
        for member in class_def['body']:
            if member['type'] == 'VARIABLE_DECLARATION':
                self._analyze_variable_declaration(member, errors)
            elif member['type'] == 'METHOD_DEFINITION':
                self.analyze_method_definition(member, errors)
            else:
                errors.append(f"Warning: Unsupported member type '{member['type']}' in class '{class_name}'.")
        self.exit_scope()
        self.current_class = None

    # Validates a method definition within a class
    def analyze_method_definition(self, method, errors):
        if 'method_name' not in method or 'body' not in method:
            errors.append("Method definition must have 'method_name' and 'body' fields.")
            return
        method_name = method['method_name']
        return_type = method.get('return_type', 'void')
        params = method.get('parameters', [])
        for param in params:
            if 'name' not in param or 'type' not in param:
                errors.append("Method parameter must have 'name' and 'type' fields.")
        if self.current_class is None:
            errors.append("Error: Method definition outside of a class.")
            return
        class_info = self.scope_stack[0].get(self.current_class)
        if method_name in class_info['members']:
            errors.append(f"Error: Method '{method_name}' already declared in class '{self.current_class}'.")
        else:
            class_info['members'][method_name] = {
                'type': 'method',
                'return_type': return_type,
                'params': {param['name']: param['type'] for param in params}
            }
        self.enter_scope()
        for param in params:
            self.declare_variable(param['name'], param['type'], errors)
        self.analyze_block(method['body'], errors)
        self.exit_scope()

    # Checks the semantics of a for loop, including its components
    def analyze_for_loop(self, for_loop, errors):
        if 'init' not in for_loop or 'condition' not in for_loop or 'increment' not in for_loop or 'body' not in for_loop:
            errors.append("For loop must have 'init', 'condition', 'increment', and 'body' fields.")
            return
        if for_loop['init']['type'] == 'VARIABLE_DECLARATION':
            self._analyze_variable_declaration(for_loop['init'], errors)
        elif for_loop['init']['type'] == 'ASSIGNMENT':
            self.check_assignment(for_loop['init'], errors)
        else:
            errors.append(f"Unsupported initialization type '{for_loop['init']['type']}' in for loop.")
        condition_type = self.evaluate_expression_type(for_loop['condition'], errors, "for loop condition")
        if condition_type is not None and condition_type != 'bool':
            errors.append(f"Error: Condition in for loop should evaluate to 'bool', got {condition_type}.")
        if 'var_name' in for_loop['increment']:
            var_type = self.lookup_variable(for_loop['increment']['var_name'])
            if var_type is None:
                errors.append(f"Error: Variable '{for_loop['increment']['var_name']}' for increment not declared.")
            elif var_type not in ['int', 'float']:
                errors.append(f"Warning: Increment operation on non-numeric type '{var_type}' for variable '{for_loop['increment']['var_name']}'.")
        else:
            if 'expression' in for_loop['increment']:
                self.evaluate_expression_type(for_loop['increment']['expression'], errors, "for loop increment")
        self.analyze_statement(for_loop['body'], errors)