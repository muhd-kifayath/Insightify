import ast
import json
from collections import defaultdict
import os
from radon.complexity import cc_visit
from radon.metrics import h_visit, mi_visit
from radon.visitors import HalsteadVisitor
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
        self.attach_parents(self.tree)
        self.visit_ast()

    def attach_parents(self, node, parent=None):
        node.parent = parent
        for child in ast.iter_child_nodes(node):
            self.attach_parents(child, node)

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
        total_complexity = sum([block.complexity for block in complexities])
        return total_complexity

    def calculate_halstead_metrics(self):
        halstead_metrics = h_visit(self.code)
        total = halstead_metrics.total
        return {
            'unique_operators': total.h1,
            'unique_operands': total.h2,
            'total_operators': total.N1,
            'total_operands': total.N2,
            'volume': total.volume,
            'effort': total.effort
        }

    def calculate_maintainability_index(self):
        return mi_visit(self.code, multi=False) or 0

    def calculate_DIT(self):
        inheritance_depths = [
            self.get_inheritance_depth(cls['node']) for cls in self.classes.values()
        ]
        return max(inheritance_depths, default=0)

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
            methods = cls_info['methods']
            for method_name in methods:
                method_node = self.get_method_node(cls_info['node'], method_name)
                if method_node:
                    external_calls = self.get_external_calls(method_node)
                    coupling += len(external_calls)
        return coupling

    def get_method_node(self, class_node, method_name):
        for body_item in class_node.body:
            if isinstance(body_item, ast.FunctionDef) and body_item.name == method_name:
                return body_item
        return None

    def get_external_calls(self, node):
        external_calls = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    external_calls.add(child.func.attr)
                elif isinstance(child.func, ast.Name):
                    external_calls.add(child.func.id)
        return external_calls

    def calculate_LCOM(self):
        lcom_values = []
        for cls_info in self.classes.values():
            methods = cls_info['methods']
            attributes = cls_info['attributes']
            method_attr_usage = [
                self.get_method_attributes(cls_info['node'], method_name) for method_name in methods
            ]
            P, Q = 0, 0
            for i in range(len(method_attr_usage)):
                for j in range(i + 1, len(method_attr_usage)):
                    if method_attr_usage[i].intersection(method_attr_usage[j]):
                        Q += 1
                    else:
                        P += 1
            lcom = max(0, P - Q)
            lcom_values.append(lcom)
        return sum(lcom_values) / len(lcom_values) if lcom_values else 0

    def get_method_attributes(self, class_node, method_name):
        method_node = self.get_method_node(class_node, method_name)
        attr_visitor = AttributeVisitor()
        attr_visitor.visit(method_node)
        return attr_visitor.attributes

    def calculate_FanIn_FanOut(self):
        fan_in = defaultdict(int)
        fan_out = defaultdict(int)
        for func, calls in self.calls.items():
            fan_out[func] = len(calls)
            for called_func in calls:
                fan_in[called_func] += 1
        return sum(fan_in.values()), sum(fan_out.values())

    def calculate_NOM(self):
        return sum(len(cls_info['methods']) for cls_info in self.classes.values())

class AttributeVisitor(ast.NodeVisitor):
    def __init__(self):
        self.attributes = set()

    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name) and node.value.id == 'self':
            self.attributes.add(node.attr)
        self.generic_visit(node)

def calculate_mccall_metrics(metrics):
    max_values = {
        'cyclomatic_complexity': 50,
        'comment_density': 1.0,
        'maintainability_index': 100,
        'cbo': 20,
        'lcom': 100,
        'fan_in': 50,
        'fan_out': 50,
        'loc': 1000,
        'dit': 10,
        'effort': 1000

        # max_complexity = 150
        # max_comment_density = 100
        # max_mi = 100
        # max_cbo = 200
        # max_lcom = 100
        # max_fan_in = 100
        # max_fan_out = 100
        # max_loc = 1000
        # max_dit = 10
    }
    return {
        "Modifiability": 0.4 * (1 - (metrics['cyclomatic_complexity'] / max_values['cyclomatic_complexity'])) +
                        0.3 * (metrics['comment_density'] / max_values['comment_density']) +
                        0.3 * (metrics['maintainability_index'] / max_values['maintainability_index']),
        "Testability": 0.5 * (1 - (metrics['cyclomatic_complexity'] / max_values['cyclomatic_complexity'])) +
                       0.5 * (metrics['maintainability_index'] / max_values['maintainability_index']),
        "Reliability": 0.4 * (1 - (metrics['cyclomatic_complexity'] / max_values['cyclomatic_complexity'])) +
                       0.3 * (1 - (metrics['cbo'] / max_values['cbo'])) +
                       0.3 * (metrics['lcom'] / max_values['lcom']),
        "Understandability": 0.35 * (metrics['comment_density'] / max_values['comment_density']) +
                             0.25 * (1 - (metrics['fan_in'] / max_values['fan_in'])) +
                             0.25 * (1 - (metrics['fan_out'] / max_values['fan_out'])) +
                             0.15 * (1 - (metrics['loc'] / max_values['loc'])),
        "Self-Descriptiveness": 0.5 * (metrics['comment_density'] / max_values['comment_density']) +
                                0.5 * (metrics['loc'] / max_values['loc']),
        "Reusability": 0.5 * (1 - (metrics['cbo'] / max_values['cbo'])) +
                       0.5 * (1 - (metrics['dit'] / max_values['dit'])),
        "Portability": 0.7 * (1 - (metrics['loc'] / max_values['loc'])) +
                       0.3 * (1 - (metrics['cyclomatic_complexity'] / max_values['cyclomatic_complexity'])),
        "Efficiency": max(0, min((0.4 * (1 - metrics['cyclomatic_complexity'] / max_values['cyclomatic_complexity']) +
                                0.4 * (1 - metrics['halstead_metrics']['effort'] / max_values['effort']) +
                                0.2 * (1 - metrics['loc'] / max_values['loc'])
                    ), 1)),
    }

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python code_metrics_integrated.py <filepath>")
        sys.exit(1)
    filepath = sys.argv[1]
    analyzer = CodeMetricsAnalyzer(filepath)
    
    halstead_metrics = analyzer.calculate_halstead_metrics()
    metrics_unformatted = {
        "cyclomatic_complexity": analyzer.calculate_cyclomatic_complexity(),
        "comment_density": analyzer.calculate_comment_density(),
        "maintainability_index": analyzer.calculate_maintainability_index(),
        "cbo": analyzer.calculate_CBO(),
        "lcom": analyzer.calculate_LCOM(),
        "halstead_metrics": halstead_metrics,
        "fan_in": analyzer.calculate_FanIn_FanOut()[0],
        "fan_out": analyzer.calculate_FanIn_FanOut()[1],
        "loc": analyzer.calculate_LOC(),
        "dit": analyzer.calculate_DIT()
    }

    metrics = {
        "Lines of Code (LOC)": analyzer.calculate_LOC(),
        "Comment Density": analyzer.calculate_comment_density(),
        "Cyclomatic Complexity": analyzer.calculate_cyclomatic_complexity(),
        "Maintainability Index": analyzer.calculate_maintainability_index(),
        "Halstead Metrics": "",
        "Unique Operators": halstead_metrics['unique_operators'],
        "Unique Operands": halstead_metrics['unique_operands'],
        "Total Operators": halstead_metrics['total_operators'],
        "Total Operands": halstead_metrics['total_operands'],
        "Volume": halstead_metrics['volume'],
        "Effort": halstead_metrics['effort'],
        "Depth of Inheritance Tree (DIT)": analyzer.calculate_DIT(),
        "Coupling Between Object classes (CBO)": analyzer.calculate_CBO(),
        "Lack of Cohesion of Methods (LCOM)": analyzer.calculate_LCOM(),
        "Fan-in": analyzer.calculate_FanIn_FanOut()[0],
        "Fan-out": analyzer.calculate_FanIn_FanOut()[1],
        "Number of Methods (NOM)": analyzer.calculate_NOM()
    }
    mccall_metrics = calculate_mccall_metrics(metrics_unformatted)
    combined_metrics = {
        'static_metrics': metrics,
        'intermediate_level_metrics': mccall_metrics
    }

    output_filename = f"{filepath[:-3]}_metrics.json"
    with open(output_filename, 'w') as f:
        json.dump(combined_metrics, f, indent=4)
    print(f"Metrics saved to '{output_filename}'.")

