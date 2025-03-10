import json

# Function definitions (unchanged)
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

# Main function
if __name__ == "__main__":
    # Load metrics from JSON file
    json_file = "metrics.json"  # Replace with the actual file path
    with open(json_file, 'r') as f:
        metrics = json.load(f)

    # Extract values
    cyclomatic_complexity = metrics.get("cyclomatic_complexity", 0)
    comment_density = metrics.get("comment_density", 0)
    maintainability_index = metrics.get("maintainability_index", 0)
    cbo = metrics.get("cbo", 0)
    lcom = metrics.get("lcom", 0)
    fan_in = metrics.get("fan_in", 0)
    fan_out = metrics.get("fan_out", 0)
    loc = metrics.get("loc", 0)
    dit = metrics.get("dit", 0)

    # Define maximum values (adjust as needed for your project)
    max_complexity = 150
    max_comment_density = 100
    max_mi = 100
    max_cbo = 200
    max_lcom = 100
    max_fan_in = 100
    max_fan_out = 100
    max_loc = 1000
    max_dit = 10

    # Calculate McCall's Quality Metrics
    metrics_results = {
        "Modifiability": calculate_modifiability(cyclomatic_complexity, max_complexity, comment_density, max_comment_density, maintainability_index, max_mi),
        "Testability": calculate_testability(cyclomatic_complexity, max_complexity, maintainability_index, max_mi),
        "Reliability": calculate_reliability(cyclomatic_complexity, max_complexity, cbo, max_cbo, lcom, max_lcom),
        "Understandability": calculate_understandability(comment_density, max_comment_density, fan_in, max_fan_in, fan_out, max_fan_out, loc, max_loc),
        "Self-Descriptiveness": calculate_self_descriptiveness(comment_density, max_comment_density, loc, max_loc),
        "Reusability": calculate_reusability(cbo, max_cbo, dit, max_dit),
        "Portability": calculate_portability(loc, max_loc, cyclomatic_complexity, max_complexity)
    }

    # Export results to a JSON file
    output_file = "quality_metrics_results.json"  # Replace with the desired output file path
    with open(output_file, 'w') as f:
        json.dump(metrics_results, f, indent=4)
