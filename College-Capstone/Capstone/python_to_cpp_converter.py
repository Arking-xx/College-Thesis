# Class to convert Python AST to C++ code
class PythonToCppConverter:
    def __init__(self, ast):
        self.ast = ast  # Abstract Syntax Tree from Python code
        self.variables = set()  # Track declared variables
        self.declarations = []  # Store variable declarations
        self.statements = []  # Store executable statements

    # Generate complete C++ code from AST
    def generate_code(self):
        self.process_program(self.ast)
        declarations = "\n".join(self.declarations)
        statements = "\n".join(self.statements)
        return f"#include <iostream>\n#include <string>\nusing namespace std;\n\nint main() {{\n{declarations}\n{statements}\n    return 0;\n}}"

    # Process the root PROGRAM node
    def process_program(self, node):
        if node["type"] == "PROGRAM":
            for stmt in node["statements"]:
                result = self.process_node(stmt)
                if result:
                    # Separate declarations from statements
                    if stmt["type"] == "ASSIGNMENT" and stmt["var_name"] not in self.variables:
                        self.declarations.append(result.rstrip())
                    else:
                        self.statements.append(result.rstrip())

    # Process individual AST nodes
    def process_node(self, node):
        print(f"Processing node: {node['type']}")
        if node["type"] == "ASSIGNMENT":
            var_name = node["var_name"]
            expr = node["expression"]
            # Handle compound assignments (e.g., i += 1)
            if (expr["type"] == "BINARY_EXPRESSION" and 
                expr["operator"] in ["+", "-", "*", "/", "%"] and 
                expr["left"]["type"] == "IDENTIFIER" and 
                expr["left"]["value"] == var_name):
                operator = expr["operator"]
                right = self.generate_expression(expr["right"])
                if var_name not in self.variables:
                    self.variables.add(var_name)
                    var_type = self.determine_value_type(expr["right"])
                    if var_type == "string":
                        return f"    string {var_name} = {right};\n    {var_name} {operator}= {right};"
                    elif var_type == "number":
                        return f"    int {var_name} = {right};\n    {var_name} {operator}= {right};"
                    else:
                        return f"    auto {var_name} = {right};\n    {var_name} {operator}= {right};"
                return f"    {var_name} {operator}= {right};"
            # Regular assignment
            expr_result = self.generate_expression(expr, var_name)
            if var_name not in self.variables:
                self.variables.add(var_name)
                var_type = self.determine_value_type(expr)
                if var_type == "string":
                    if expr_result.startswith("    cout"):
                        return f"    string {var_name};\n{expr_result}"
                    return f"    string {var_name} = {expr_result};"
                elif var_type == "number":
                    if expr_result.startswith("    cout"):
                        return f"    int {var_name};\n{expr_result}"
                    return f"    int {var_name} = {expr_result};"
                else:
                    return f"    auto {var_name} = {expr_result};"
            return f"    {var_name} = {expr_result};" if expr_result else ""
        elif node["type"] == "PRINT_STATEMENT":
            # Convert Python print to C++ cout
            cpp_args = [self.generate_expression(arg, wrap_binary=True) for arg in node["args"]]
            result = f'    cout << {" << ".join(cpp_args)} << endl;'
            print(f"PRINT result: {result}")
            return result
        elif node["type"] == "IF_STATEMENT":
            # Handle if/elif/else constructs
            condition = self.generate_expression(node["condition"])
            true_branch = node["true_branch"]
            if true_branch["type"] == "BLOCK":
                body_lines = [self.process_node(stmt) for stmt in true_branch["statements"]]
                body = "\n".join(f"        {line}" for line in body_lines if line)
            else:
                body = self.process_node(true_branch)
                body = f"        {body}" if body else ""
            result = f'    if ({condition}) {{\n{body}\n    }}'
            false_branch = node.get("false_branch")
            while false_branch:
                if false_branch["type"] == "IF_STATEMENT":
                    elif_condition = self.generate_expression(false_branch["condition"])
                    elif_true_branch = false_branch["true_branch"]
                    if elif_true_branch["type"] == "BLOCK":
                        elif_body_lines = [self.process_node(stmt) for stmt in elif_true_branch["statements"]]
                        elif_body = "\n".join(f"        {line}" for line in elif_body_lines if line)
                    else:
                        elif_body = self.process_node(elif_true_branch)
                        elif_body = f"        {elif_body}" if elif_body else ""
                    result += f'\n    else if ({elif_condition}) {{\n{elif_body}\n    }}'
                    false_branch = false_branch.get("false_branch")
                elif false_branch["type"] == "BLOCK":
                    else_body_lines = [self.process_node(stmt) for stmt in false_branch["statements"]]
                    else_body = "\n".join(f"        {line}" for line in else_body_lines if line)
                    result += f'\n    else {{\n{else_body}\n    }}'
                    break
                else:
                    else_body = self.process_node(false_branch)
                    else_body = f"        {else_body}" if else_body else ""
                    result += f'\n    else {{\n{else_body}\n    }}'
                    break
            print(f"Full IF result: {result}")
            return result
        elif node["type"] == "WHILE_LOOP":
            # Convert Python while to C++ while
            condition = self.generate_expression(node["condition"])
            body_lines = [self.process_node(stmt) for stmt in node["body"]]
            body = "\n".join(f"        {line.rstrip()}" for line in body_lines if line)
            result = f'    while ({condition}) {{\n{body}\n    }}'
            print(f"WHILE condition: {condition}, body: {body}")
            print(f"Full WHILE result: {result}")
            return result
        elif node["type"] == "FOR_LOOP":
            # Convert Python for to C++ for
            iterator = node["iterator"]
            start = self.generate_expression(node["start"]) if "start" in node else "0"
            stop = self.generate_expression(node["stop"]) if "stop" in node else self.generate_expression(node["limit"])
            step = self.generate_expression(node["step"]) if "step" in node else "1"
            body_lines = [self.process_node(stmt) for stmt in node["body"]]
            body = "\n".join(f"        {line.rstrip()}" for line in body_lines if line)
            increment = f"{iterator}++" if step == "1" else f"{iterator} += {step}"
            if iterator not in self.variables:
                self.variables.add(iterator)
                result = f"    for (int {iterator} = {start}; {iterator} < {stop}; {increment}) {{\n{body}\n    }}"
            else:
                result = f"    for ({iterator} = {start}; {iterator} < {stop}; {increment}) {{\n{body}\n    }}"
            print(f"FOR_LOOP iterator: {iterator}, start: {start}, stop: {stop}, step: {step}, body: {body}")
            print(f"Full FOR_LOOP result: {result}")
            return result
        elif node["type"] == "BLOCK":
            # Process block statements
            body_lines = [self.process_node(stmt) for stmt in node["statements"]]
            body = "\n".join(f"    {line.strip()}" for line in body_lines if line)
            print(f"BLOCK content: {body}")
            return body
        return ""

    # Generate C++ expressions from AST nodes
    def generate_expression(self, node, target_var=None, wrap_binary=False):
        if node["type"] == "STRING_LITERAL":
            return f'"{node["value"][1:-1]}"'  # Strip Python quotes
        elif node["type"] == "IDENTIFIER":
            return node["value"]
        elif node["type"] == "NUMBER":
            return node["value"]
        elif node["type"] == "BINARY_EXPRESSION":
            left = self.generate_expression(node["left"])
            right = self.generate_expression(node["right"])
            expr = f"{left} {node['operator']} {right}"
            return f"({expr})" if wrap_binary else expr
        elif node["type"] == "FUNCTION_CALL":
            func_name = node["func_name"]
            args = [self.generate_expression(arg) for arg in node["args"]]
            if func_name == "input" and target_var:
                prompt = args[0] if args else '""'
                return f'    cout << {prompt};\n    cin >> {target_var};'
            elif func_name == "int" and target_var:
                nested_input = node["args"][0]
                if nested_input["type"] == "FUNCTION_CALL" and nested_input["func_name"] == "input":
                    prompt = self.generate_expression(nested_input["args"][0]) if nested_input["args"] else '""'
                    return f'    cout << {prompt};\n    cin >> {target_var};'
            return ""
        return ""

    # Infer variable type from expression
    def determine_value_type(self, node):
        if node["type"] == "NUMBER":
            return "number"
        elif node["type"] == "STRING_LITERAL":
            return "string"
        elif node["type"] == "FUNCTION_CALL":
            if node["func_name"] == "input":
                return "string"
            elif node["func_name"] == "int":
                return "number"
        elif node["type"] == "BINARY_EXPRESSION" and node["operator"] == "+":
            left_type = self.determine_value_type(node["left"])
            right_type = self.determine_value_type(node["right"])
            if "string" in (left_type, right_type):
                return "string"
            return "number"
        return "unknown"