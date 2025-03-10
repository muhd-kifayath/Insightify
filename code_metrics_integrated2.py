import ast
import os
import json
from radon.complexity import cc_visit
from radon.metrics import h_visit, mi_visit
from radon.visitors import HalsteadVisitor
from collections import defaultdict
import networkx as nx
import sys

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

        # Set parent attributes for all AST nodes
        self.attach_parents(self.tree)

        self.visit_ast()

    def attach_parents(self, node, parent=None):
        """
        Recursively attach a 'parent' attribute to each node in the AST.
        """
        node.parent = parent
        for child in ast.iter_child_nodes(node):
            self.attach_parents(child, node)

    def visit_ast(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef):
                self.process_class(node)
            elif isinstance(node, ast.FunctionDef):
                self.process_function(node)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
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

    def calculate_LOC(self):
        code_lines = [line for line in self.lines if line.strip()]
        return len(code_lines)

    def calculate_comment_density(self):
        comment_lines = [line for line in self.lines if line.strip().startswith('#')]
        code_lines = [line for line in self.lines if line.strip() and not line.strip().startswith('#')]
        return len(comment_lines) / len(code_lines) if code_lines else 0

    def calculate_cyclomatic_complexity(self):
        complexities = cc_visit(self.code)
        return sum([block.complexity for block in complexities])

    def calculate_halstead_metrics(self):
        halstead_metrics = h_visit(self.code).total
        return (
            halstead_metrics.h1,  # Unique operators
            halstead_metrics.h2,  # Unique operands
            halstead_metrics.N1,  # Total operators
            halstead_metrics.N2,  # Total operands
            halstead_metrics.volume,
            halstead_metrics.effort
        )

    def calculate_maintainability_index(self):
        mi_score = mi_visit(self.code, multi=False)
        return mi_score if mi_score is not None else 0

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
        for cls_info in self.classes.values():
            for method_name in cls_info['methods']:
                method_node = self.get_method_node(cls_info['node'], method_name)
                if method_node:
                    external_calls = self.get_external_calls(method_node, cls_info['node'].name)
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
        for cls_info in self.classes.values():
            methods = cls_info['methods']
            attributes = cls_info['attributes']
            method_attribute_usage = []
            for method_name in methods:
                method_node = self.get_method_node(cls_info['node'], method_name)
                attr_visitor = AttributeVisitor()
                attr_visitor.visit(method_node)
                method_attribute_usage.append(attr_visitor.attributes)
            P = 0
            Q = 0
            for i in range(len(method_attribute_usage)):
                for j in range(i + 1, len(method_attribute_usage)):
                    if method_attribute_usage[i].intersection(method_attribute_usage[j]):
                        Q += 1
                    else:
                        P += 1
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
        return sum(fan_in.values()), sum(fan_out.values())

    def calculate_NOM(self):
        return sum([len(cls_info['methods']) for cls_info in self.classes.values()])

class AttributeVisitor(ast.NodeVisitor):
    def __init__(self):
        self.attributes = set()

    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name) and node.value.id == 'self':
            self.attributes.add(node.attr)
        self.generic_visit(node)

# McCall's quality metrics calculation functions
def calculate_modifiability(cyclomatic_complexity, max_complexity, comment_density, max_comment_density, maintainability_index, max_mi):
    return (
        0.4 * (1 - (cyclomatic_complexity / max_complexity)) +
        0.3 * (comment_density / max_comment_density) +
        0.3 * (maintainability_index / max_mi)
    )

def calculate_testability(cyclomatic_complexity, max_complexity, maintainability_index, max_mi):
    return (
        0.5 * (1 - (cyclomatic_complexity / max_complexity)) +
        0.5 * (maintainability_index / max_mi)
    )

def calculate_reliability(cyclomatic_complexity, max_complexity, cbo, max_cbo, lcom, max_lcom):
    return (
        0.4 * (1 - (cyclomatic_complexity / max_complexity)) +
        0.3 * (1 - (cbo / max_cbo)) +
        0.3 * (lcom / max_lcom)
    )

def calculate_understandability(comment_density, max_comment_density, fan_in, max_fan_in, fan_out, max_fan_out, loc, max_loc):
    return (
        0.35 * (comment_density / max_comment_density) +
        0.25 * (1 - (fan_in / max_fan_in)) +
        0.25 * (1 - (fan_out / max_fan_out)) +
        0.15 * (1 - (loc / max_loc))
    )

def calculate_self_descriptiveness(comment_density, max_comment_density, loc, max_loc):
    return (
        0.5 * (comment_density / max_comment_density) +
        0.5 * (loc / max_loc)
    )

def calculate_reusability(cbo, max_cbo, dit, max_dit):
    return (
        0.5 * (1 - (cbo / max_cbo)) +
        0.5 * (1 - (dit / max_dit))
    )

def calculate_portability(loc, max_loc, cyclomatic_complexity, max_complexity):
    return (
        0.7 * (1 - (loc / max_loc)) +
        0.3 * (1 - (cyclomatic_complexity / max_complexity))
    )


def analyze_code(filepath):
    analyzer = CodeMetricsAnalyzer(filepath)
    
    loc = analyzer.calculate_LOC()
    comment_density = analyzer.calculate_comment_density()
    cyclomatic_complexity = analyzer.calculate_cyclomatic_complexity()
    maintainability_index = analyzer.calculate_maintainability_index()
    DIT = analyzer.calculate_DIT()
    cbo = analyzer.calculate_CBO()
    lcom = analyzer.calculate_LCOM()
    fan_in, fan_out = analyzer.calculate_FanIn_FanOut()
    nom = analyzer.calculate_NOM()

    # Static code metrics output
    static_metrics = {
        "Lines of Code (LOC)": loc,
        "Comment Density": comment_density,
        "Cyclomatic Complexity": cyclomatic_complexity,
        "Maintainability Index": maintainability_index,
        "Depth of Inheritance Tree (DIT)": DIT,
        "Coupling Between Object classes (CBO)": cbo,
        "Lack of Cohesion of Methods (LCOM)": lcom,
        "Fan-in": fan_in,
        "Fan-out": fan_out,
        "Number of Methods (NOM)": nom
    }

    # Defining maximum thresholds for normalization
    max_values = {
        "Max Cyclomatic Complexity": 50,  # Hypothetical maximum complexity
        "Max Comment Density": 1,         # Maximum possible comment density
        "Max Maintainability Index": 100, # Maximum MI score
        "Max CBO": 10,                    # Assumed maximum CBO
        "Max LCOM": 10,                   # Assumed maximum LCOM
        "Max Fan-in": 20,                 # Assumed maximum fan-in
        "Max Fan-out": 20,                # Assumed maximum fan-out
        "Max LOC": 1000                   # Assumed max LOC for scaling
    }

    # Calculating McCall's intermediate quality metrics
    modifiability = calculate_modifiability(
        cyclomatic_complexity, max_values["Max Cyclomatic Complexity"],
        comment_density, max_values["Max Comment Density"],
        maintainability_index, max_values["Max Maintainability Index"]
    )

    testability = calculate_testability(
        cyclomatic_complexity, max_values["Max Cyclomatic Complexity"],
        maintainability_index, max_values["Max Maintainability Index"]
    )

    reliability = calculate_reliability(
        cyclomatic_complexity, max_values["Max Cyclomatic Complexity"],
        cbo, max_values["Max CBO"],
        lcom, max_values["Max LCOM"]
    )

    understandability = calculate_understandability(
        comment_density, max_values["Max Comment Density"],
        fan_in, max_values["Max Fan-in"],
        fan_out, max_values["Max Fan-out"],
        loc, max_values["Max LOC"]
    )

    self_descriptiveness = calculate_self_descriptiveness(
        comment_density, max_values["Max Comment Density"]
    )

    

    intermediate_metrics = {
        "Modifiability": modifiability,
        "Testability": testability,
        "Reliability": reliability,
        "Understandability": understandability,
        "Self-Descriptiveness": self_descriptiveness
    }

    # Combine metrics into a unified JSON output
    combined_metrics = {
        "Static Code Metrics": static_metrics,
        "McCall's Intermediate Quality Metrics": intermediate_metrics
    }

    # Outputting the metrics as a JSON file
    output_filepath = os.path.splitext(filepath)[0] + "_metrics.json"
    with open(output_filepath, 'w', encoding='utf-8') as f:
        json.dump(combined_metrics, f, indent=4)

    print(f"Analysis complete. Metrics saved to {output_filepath}")

# Run the analysis on a sample Python file
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python code_metrics_integrated.py <file_to_analyze>")
        sys.exit(1)

    file_to_analyze = sys.argv[1]
    analyze_code(file_to_analyze)
