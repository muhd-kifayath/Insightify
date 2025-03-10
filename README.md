# Insightify: Automated Software Quality Assessment System

## Overview
Insightify is a modular, AI-powered framework designed to automate software quality assessment through static code analysis, metric evaluation, and intelligent report generation. The system integrates traditional software metrics with AI-driven insights to provide a comprehensive evaluation of software maintainability, efficiency, and reliability.

## Features
- **Static Code Analysis**: Computes various software quality metrics such as complexity, maintainability, cohesion, and coupling.
- **McCall’s Model-Based Evaluation**: Converts raw static metrics into interpretable software quality attributes.
- **AI-Powered Insights**: Utilizes GPT-based models to generate intelligent assessments based on computed metrics.
- **Automated Report Generation**: Formats extracted metrics into structured, human-readable PDF reports.
- **Scalability & Modularity**: Supports multiple programming languages and customizable metric computation techniques.

## System Architecture
The system follows a structured workflow composed of distinct modules:
1. **Application Module**: Extracts source code for analysis.
2. **Metric-o-meter Module**: Computes static metrics and derives intermediate quality attributes using McCall’s Model.
3. **Data Export**: Stores computed metrics in JSON format for structured processing.
4. **PDF Formatter Module**: Formats extracted metrics and generates a PDF report.
5. **GPT Integration Module**: AI-powered insights based on computed metrics.

## Installation
### Prerequisites
- Python 3.x
- Required dependencies listed in `requirements.txt`
- GPT API access (if using AI integration)

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/muhd-kifayath/Insightify.git
   cd Insightify
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the system:
   ```bash
   python pdfreport.py <code_file>
   ```

## Usage
1. Provide the source code to be analyzed.
2. The system computes static metrics and quality attributes.
3. The generated JSON file is used for AI-driven insights and PDF report creation.
4. The final report is saved in the `output/` directory.


## License
This project is licensed under the MIT License. 


