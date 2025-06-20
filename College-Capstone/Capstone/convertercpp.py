import os
print(f"Running file: {os.path.realpath(__file__)}")

from semantic_analyzer_cpp import SemanticAnalyzer

# Converts an AST into Python code with optional main function wrapping
class Converter:
    def __init__(self, data, use_main=False):
        self.ast = data
        self.use_main = use_main

    # Generates Python code from the AST after semantic analysis
    def generate_code(self):
        semantic_analyzer = SemanticAnalyzer()
        errors = semantic_analyzer.analyze(self.ast)
        if errors:
            print("Semantic Errors:", "\n".join(errors))
            return ""
        self.semantic_analyzer = semantic_analyzer
        converted_code = self.generate_node(self.ast).strip()
        if self.use_main:
            converted_code = f"def main():\n    {converted_code.replace('\n', '\n    ')}\n\nif __name__ == \"__main__\":\n    main()"
        print("Raw converted_code:", repr(converted_code))
        print("Generated Python Code:")
        print(converted_code)
        return converted_code

    # Recursively generates code for a given AST node
    def generate_node(self, node, statements=None, position=0, parent_statements=None):
        if node["type"] == "PROGRAM":
            stmts = [self.generate_node(stmt, node["statements"], i, node["statements"]) 
                     for i, stmt in enumerate(node["statements"])]
            return "\n".join(stmt.lstrip() for stmt in stmts if stmt)
        elif node["type"] == "FUNCTION_DEFINITION":
            body = [self.generate_node(stmt, node["body"], i, node["body"]) 
                    for i, stmt in enumerate(node["body"])]
            body_str = "\n".join(stmt for stmt in body if stmt.strip())
            if node["func_name"] == "main" and not self.use_main:
                return body_str
            return f"def {node['func_name']}():\n    {body_str.replace('\n', '\n    ')}"
        elif node["type"] == "IO_STATEMENT":
            if not node.get("expressions"):
                return "print()"
            # Generate expressions and handle assignments in cout
            expressions = []
            assignments = []
            for expr_node in node["expressions"]:
                if (expr_node["type"] == "BINARY_EXPRESSION" and 
                    expr_node["operator"] == "=" and 
                    node["io_operator"] == "cout"):
                    # Handle assignment inside cout
                    var_name = self.generate_node(expr_node["left"])
                    value = self.generate_node(expr_node["right"])
                    assignments.append(f"{var_name} = {value}")
                    expressions.append(var_name)  # Print the assigned variable
                else:
                    expressions.append(self.generate_node(expr_node))
            
            if node["io_operator"] == "cout":
                is_prompt = (
                    statements and
                    position + 1 < len(statements) and
                    statements[position + 1]["type"] == "IO_STATEMENT" and
                    statements[position + 1]["io_operator"] == "cin"
                )
                if is_prompt and len(expressions) == 1 and expressions[0].startswith('"'):
                    return "\n".join(assignments) if assignments else ""
                
                f_string_parts = []
                for expr in expressions:
                    if expr.startswith('"') and expr.endswith('"'):
                        cleaned_expr = expr.strip('"').replace('\\n', '')
                        if cleaned_expr:
                            f_string_parts.append(cleaned_expr)
                    else:
                        f_string_parts.append(f"{{{expr}}}")
                output = f"print(f\"{''.join(f_string_parts)}\")"
                has_newline = any(expr == '"\\n"' or (expr.startswith('"') and '\\n' in expr) for expr in expressions)
                if not has_newline:
                    output = f'print(f"{"".join(f_string_parts)}")'
                
                # Combine assignments and print statement
                if assignments:
                    return "\n".join(assignments + [output])
                return output
            elif node["io_operator"] == "cin":
                var_name = expressions[0]
                var_type = self.semantic_analyzer.lookup_variable(var_name)
                if not var_type:
                    var_type = self.lookup_variable_type(var_name, statements, position)
                if statements and position > 0:
                    prev_stmt = statements[position - 1]
                    if prev_stmt["type"] == "IO_STATEMENT" and prev_stmt["io_operator"] == "cout":
                        prompt = self.generate_node(prev_stmt["expressions"][0]).strip('"')
                        if var_type == "int":
                            return f"{var_name} = int(input(\"{prompt}\"))"
                        return f"{var_name} = input(\"{prompt}\")"
                if var_type == "int":
                    return f"{var_name} = int(input())"
                return f"{var_name} = input()"
        elif node["type"] == "VARIABLE_DECLARATION":
            var_name = node["var_name"]
            if "initializer" in node:
                initializer = self.generate_node(node["initializer"])
                return f"{var_name} = {initializer}"
            return ""
        elif node["type"] == "ASSIGNMENT":
            var_name = node["var_name"]
            expression = node["expression"]
            # Check if it's a compound assignment pattern (e.g., i = i + 2)
            if (expression["type"] == "BINARY_EXPRESSION" and 
                expression["operator"] in ["+", "-", "*", "/", "%"] and
                expression["left"]["type"] == "IDENTIFIER" and
                expression["left"]["value"] == var_name):
                operator = expression["operator"]
                right = self.generate_node(expression["right"])
                return f"{var_name} {operator}= {right}"
            # Fallback to regular assignment
            expr_code = self.generate_node(expression)
            return f"{var_name} = {expr_code}"
        elif node["type"] == "EXPRESSION_STATEMENT":
            expression = self.generate_node(node["expression"])
            return expression if expression else ""
        elif node["type"] == "FOR_LOOP":
            init = node["init"]
            condition = node["condition"]
            increment = node["increment"]
            body = node["body"]
            if init["type"] == "VARIABLE_DECLARATION" and "initializer" in init:
                start = self.generate_node(init["initializer"])
            elif init["type"] == "ASSIGNMENT":
                start = self.generate_node(init["expression"])
            else:
                start = "0"
            end = self.generate_node(condition["right"])
            step = "1"
            if condition["operator"] == "<=":
                end = str(int(end) + 1)
            elif condition["operator"] == "<":
                pass
            elif condition["operator"] == ">":
                start, end = end, start
                step = "-1"
            elif condition["operator"] == ">=":
                end = str(int(end) - 1)
                step = "-1"
            if increment:
                if increment["type"] == "ASSIGNMENT":
                    incr_expr = increment["expression"]
                    if incr_expr["type"] == "BINARY_EXPRESSION":
                        if incr_expr["operator"] == "+":
                            step = self.generate_node(incr_expr["right"])
                        elif incr_expr["operator"] == "-":
                            step = f"-{self.generate_node(incr_expr['right'])}"
                elif increment["type"] == "INCREMENT":
                    step = "1" if increment["operator"] == "++" else "-1"
            var_name = init["var_name"]
            range_str = f"range({start}, {end}, {step})"
            if body["type"] == "BLOCK":
                body_str = "\n".join(self.generate_node(stmt, body["statements"], i) 
                                    for i, stmt in enumerate(body["statements"]))
            else:
                body_str = self.generate_node(body)
            return f"for {var_name} in {range_str}:\n    {body_str.replace('\n', '\n    ')}"
        elif node["type"] == "WHILE_LOOP":
            condition_str = self.generate_node(node["condition"])
            body_node = node["body"]
            if isinstance(body_node, dict) and body_node.get("type") == "BLOCK":
                body_lines = [self.generate_node(stmt, body_node["statements"], i, parent_statements) 
                              for i, stmt in enumerate(body_node["statements"])]
                body = "\n".join(line for line in body_lines if line)
            else:
                body = self.generate_node(body_node)
            return f"while {condition_str}:\n    {body.replace('\n', '\n    ')}"
        elif node["type"] == "INCREMENT":
            var_name = node["var_name"]
            if node["operator"] == "++":
                return f"{var_name} += 1"
            elif node["operator"] == "--":
                return f"{var_name} -= 1"
            else:
                raise ValueError(f"Unsupported increment operator: {node['operator']}")
        elif node["type"] == "BINARY_EXPRESSION":
            left = self.generate_node(node["left"])
            right = self.generate_node(node["right"])
            operator = node["operator"]
            return f"{left} {operator} {right}"
        elif node["type"] == "STRING_LITERAL":
            return node["value"]
        elif node["type"] == "NUMBER":
            return node["value"]
        elif node["type"] == "IDENTIFIER":
            return node["value"]
        elif node["type"] == "RETURN_STATEMENT":
            expression = self.generate_node(node["expression"])
            parent = self.find_parent(node)
            if parent and parent["type"] == "FUNCTION_DEFINITION" and parent["func_name"] != "main":
                return f"return {expression}"
            return ""
        elif node["type"] == "IF_STATEMENT":
            # Generate the condition and true branch
            condition = self.generate_node(node["condition"])
            true_branch = node["true_branch"]
            if true_branch["type"] == "BLOCK":
                body_lines = [self.generate_node(stmt, true_branch["statements"], i, true_branch["statements"])
                              for i, stmt in enumerate(true_branch["statements"])]
                true_branch_str = "\n".join(line for line in body_lines if line)
            else:
                true_branch_str = self.generate_node(true_branch)
            true_branch_str = true_branch_str.replace('\n', '\n    ')
            result = f"if {condition}:\n    {true_branch_str}"

            # Handle the false branch recursively for elif and else
            def process_false_branch(fb_node):
                nonlocal result
                if fb_node is None:
                    return
                if fb_node["type"] == "IF_STATEMENT":  # Handle else if as elif
                    next_condition = self.generate_node(fb_node["condition"])
                    next_true_branch = fb_node["true_branch"]
                    if next_true_branch["type"] == "BLOCK":
                        next_body_lines = [self.generate_node(stmt, next_true_branch["statements"], i, next_true_branch["statements"])
                                           for i, stmt in enumerate(next_true_branch["statements"])]
                        next_true_branch_str = "\n".join(line for line in next_body_lines if line)
                    else:
                        next_true_branch_str = self.generate_node(next_true_branch)
                    next_true_branch_str = next_true_branch_str.replace('\n', '\n    ')
                    result += f"\nelif {next_condition}:\n    {next_true_branch_str}"
                    # Recursively process the next false branch
                    if "false_branch" in fb_node and fb_node["false_branch"] is not None:
                        process_false_branch(fb_node["false_branch"])
                else:  # Handle plain else
                    if fb_node["type"] == "BLOCK":
                        body_lines = [self.generate_node(stmt, fb_node["statements"], i, fb_node["statements"])
                                      for i, stmt in enumerate(fb_node["statements"])]
                        false_branch_str = "\n".join(line for line in body_lines if line)
                    else:
                        false_branch_str = self.generate_node(fb_node)
                    false_branch_str = false_branch_str.replace('\n', '\n    ')
                    result += f"\nelse:\n    {false_branch_str}"

            # Process the false branch if it exists
            if "false_branch" in node and node["false_branch"] is not None:
                process_false_branch(node["false_branch"])
            return result
        return ""

    # Looks up a variable's type in the AST if not found by the semantic analyzer
    def lookup_variable_type(self, var_name, statements, position):
        if not statements or not isinstance(statements, list):
            return None
        for i in range(position - 1, -1, -1):
            stmt = statements[i]
            if (isinstance(stmt, dict) and stmt.get("type") == "VARIABLE_DECLARATION" and 
                stmt.get("var_name") == var_name):
                return stmt.get("var_type")
        return None

    # Finds the initial value of a variable in the AST
    def lookup_initial_value(self, var_name, statements, position):
        if not statements or not isinstance(statements, list):
            return None
        for i in range(position - 1, -1, -1):
            stmt = statements[i]
            if (isinstance(stmt, dict) and stmt.get("type") == "VARIABLE_DECLARATION" and 
                stmt.get("var_name") == var_name and "initializer" in stmt):
                return self.generate_node(stmt["initializer"])
        return None

    # Locates the parent node of a given node in the AST
    def find_parent(self, node):
        def search(n, target):
            if "statements" in n:
                for stmt in n["statements"]:
                    if stmt == target:
                        return n
                    result = search(stmt, target)
                    if result:
                        return result
            if "body" in n:
                if isinstance(n["body"], list):
                    for stmt in n["body"]:
                        if stmt == target:
                            return n
                        result = search(stmt, target)
                        if result:
                            return result
                elif isinstance(n["body"], dict) and "statements" in n["body"]:
                    for stmt in n["body"]["statements"]:
                        if stmt == target:
                            return n
                        result = search(stmt, target)
                        if result:
                            return result
            return None
        return search(self.ast, node)