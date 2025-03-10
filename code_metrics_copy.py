import ast
import os
from radon.complexity import cc_visit
from radon.metrics import h_visit, mi_visit
from radon.visitors import HalsteadVisitor
from collections import defaultdict
import networkx as nx

class CodeMetricsAnalyzer:
    def __init__(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            self.code = f.read()
        self.tree = ast.parse(self.code)
        self.lines = self.code.splitlines()
        self.filepath = filepath
        self.classes = {}
        self.functions = {}
        self.imports = []
        self.calls = defaultdict(list)
        self.visit_ast()

    def visit_ast(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef):
                self.process_class(node)
            elif isinstance(node, ast.FunctionDef):
                self.process_function(node)
            elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                self.process_import(node)
            elif isinstance(node, ast.Call):
                self.process_call(node)

    def process_class(self, node):
        bases = [base.id if isinstance(base, ast.Name) else None for base in node.bases]
        self.classes[node.name] = {
            'node': node,
            'methods': [],
            'bases': bases,
            'attributes': set()
        }
        for body_item in node.body:
            if isinstance(body_item, ast.FunctionDef):
                self.classes[node.name]['methods'].append(body_item.name)
                # Collect attributes used in methods
                attr_visitor = AttributeVisitor()
                attr_visitor.visit(body_item)
                self.classes[node.name]['attributes'].update(attr_visitor.attributes)

    def process_function(self, node):
        self.functions[node.name] = node

    def process_import(self, node):
        if isinstance(node, ast.Import):
            for alias in node.names:
                self.imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module
            for alias in node.names:
                self.imports.append(f"{module}.{alias.name}")

    def process_call(self, node):
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            current_func = self.get_current_function(node)
            if current_func:
                self.calls[current_func].append(func_name)

    def get_current_function(self, node):
        while node:
            if isinstance(node, ast.FunctionDef):
                return node.name
            node = node.parent
        return None

    def attach_parents(self):
        for node in ast.walk(self.tree):
            for child in ast.iter_child_nodes(node):
                child.parent = node

    def calculate_LOC(self):
        code_lines = [line for line in self.lines if line.strip()]
        return len(code_lines)

    def calculate_comment_density(self):
        comment_lines = [line for line in self.lines if line.strip().startswith('#')]
        code_lines = [line for line in self.lines if line.strip() and not line.strip().startswith('#')]
        if len(code_lines) == 0:
            return 0
        return len(comment_lines) / len(code_lines)

    def calculate_cyclomatic_complexity(self):
        complexities = cc_visit(self.code)
        total_complexity = sum([block.complexity for block in complexities])
        return total_complexity

    def calculate_halstead_metrics(self):
        visitor = HalsteadVisitor.from_code(self.code)
        return visitor.operators, visitor.operands, visitor.total_operators, visitor.total_operands, visitor.volume, visitor.effort

    def calculate_maintainability_index(self):
        mi_scores = mi_visit(self.code)
        total_mi = sum([mi for _, mi in mi_scores])
        if len(mi_scores) == 0:
            return 0
        return total_mi / len(mi_scores)

    def calculate_DIT(self):
        inheritance_depths = []
        for cls in self.classes.values():
            depth = self.get_inheritance_depth(cls['node'])
            inheritance_depths.append(depth)
        return max(inheritance_depths) if inheritance_depths else 0

    def get_inheritance_depth(self, node, depth=0):
        if not node.bases:
            return depth
        max_depth = depth
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_name = base.id
                if base_name in self.classes:
                    base_node = self.classes[base_name]['node']
                    max_depth = max(max_depth, self.get_inheritance_depth(base_node, depth + 1))
        return max_depth

    def calculate_CBO(self):
        coupling = 0
        for cls_name, cls_info in self.classes.items():
            methods = cls_info['methods']
            for method_name in methods:
                method_node = self.get_method_node(cls_info['node'], method_name)
                if method_node:
                    external_calls = self.get_external_calls(method_node, cls_name)
                    coupling += len(external_calls)
        return coupling

    def get_method_node(self, class_node, method_name):
        for body_item in class_node.body:
            if isinstance(body_item, ast.FunctionDef) and body_item.name == method_name:
                return body_item
        return None

    def get_external_calls(self, node, class_name):
        external_calls = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if isinstance(child.func.value, ast.Name) and child.func.value.id != 'self':
                        external_calls.add(child.func.attr)
                elif isinstance(child.func, ast.Name):
                    func_name = child.func.id
                    if func_name not in self.classes[class_name]['methods']:
                        external_calls.add(func_name)
        return external_calls

    def calculate_LCOM(self):
        lcom_values = []
        for cls_name, cls_info in self.classes.items():
            methods = cls_info['methods']
            attributes = cls_info['attributes']
            method_attribute_usage = []
            for method_name in methods:
                method_node = self.get_method_node(cls_info['node'], method_name)
                attr_visitor = AttributeVisitor()
                attr_visitor.visit(method_node)
                method_attribute_usage.append(attr_visitor.attributes)
            # Calculate LCOM
            P = 0  # Pairs of methods that do not share attributes
            Q = 0  # Pairs of methods that share attributes
            for i in range(len(method_attribute_usage)):
                for j in range(i + 1, len(method_attribute_usage)):
                    if method_attribute_usage[i].intersection(method_attribute_usage[j]):
                        Q += 1
                    else:
                        P += 1
            if P + Q == 0:
                lcom = 0
            else:
                lcom = (P - Q) if (P - Q) > 0 else 0
            lcom_values.append(lcom)
        return sum(lcom_values) / len(lcom_values) if lcom_values else 0

    def calculate_FanIn_FanOut(self):
        fan_in = defaultdict(int)
        fan_out = defaultdict(int)
        for func, calls in self.calls.items():
            fan_out[func] = len(calls)
            for called_func in calls:
                fan_in[called_func] += 1
        total_fan_in = sum(fan_in.values())
        total_fan_out = sum(fan_out.values())
        return total_fan_in, total_fan_out

    def calculate_NOM(self):
        total_methods = sum([len(cls_info['methods']) for cls_info in self.classes.values()])
        return total_methods

class AttributeVisitor(ast.NodeVisitor):
    def __init__(self):
        self.attributes = set()

    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name) and node.value.id == 'self':
            self.attributes.add(node.attr)
        self.generic_visit(node)

def main(filepath):
    analyzer = CodeMetricsAnalyzer(filepath)
    analyzer.attach_parents()
    loc = analyzer.calculate_LOC()
    comment_density = analyzer.calculate_comment_density()
    cyclomatic_complexity = analyzer.calculate_cyclomatic_complexity()
    operators, operands, total_ops, total_opnds, volume, effort = analyzer.calculate_halstead_metrics()
    maintainability_index = analyzer.calculate_maintainability_index()
    dit = analyzer.calculate_DIT()
    cbo = analyzer.calculate_CBO()
    lcom = analyzer.calculate_LCOM()
    fan_in, fan_out = analyzer.calculate_FanIn_FanOut()
    nom = analyzer.calculate_NOM()

    print(f"Lines of Code (LOC): {loc}")
    print(f"Comment Density: {comment_density:.2f}")
    print(f"Cyclomatic Complexity: {cyclomatic_complexity}")
    print(f"Halstead Metrics:")
    print(f"  Operators: {operators}")
    print(f"  Operands: {operands}")
    print(f"  Total Operators: {total_ops}")
    print(f"  Total Operands: {total_opnds}")
    print(f"  Volume: {volume:.2f}")
    print(f"  Effort: {effort:.2f}")
    print(f"Maintainability Index: {maintainability_index:.2f}")
    print(f"Depth of Inheritance Tree (DIT): {dit}")
    print(f"Coupling Between Objects (CBO): {cbo}")
    print(f"Lack of Cohesion of Methods (LCOM): {lcom:.2f}")
    print(f"Fan-In: {fan_in}")
    print(f"Fan-Out: {fan_out}")
    print(f"Number of Methods (NOM): {nom}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python code_metrics.py <python_source_file>")
        sys.exit(1)
    main(sys.argv[1])
