import json
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import sys
from openai import OpenAI

import re
from reportlab.platypus import PageBreak

# Set up your OpenAI API key
# # Get the API key from the environment variable
# api_key = os.environ.get("OPENAI_API_KEY")
# print(f"API Key: {api_key}")

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)


def send_to_gpt_for_analysis(code, metrics):
    # Prepare the prompt to send to the GPT model
    prompt = (
        "You are an expert software engineer and code quality analyst. "
        "Below is a Python program and its corresponding metrics. "
        "I need an analysis report on how to improve this code, identifying specific areas and suggesting improvements.\n\n"
        "Python Code:\n"
        f"{code}\n\n"
        "Code Metrics:\n"
        f"{json.dumps(metrics, indent=4)}\n\n"
        "Please provide detailed feedback on what can be improved in this code, including refactoring suggestions, best practices, and explanations of where and why changes should be made."
        "Don't give these type of starting lines, Certainly! Here's a detailed analysis of the provided Python code along with suggestions for improvements that can be made to enhance code quality, maintainability, and readability."
    )

    # Call the OpenAI API
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # Use the appropriate model available to you
        messages=[{"role": "user", "content": prompt}],
    )

    # Extract and print the response
    analysis = response.choices[0].message.content

    return analysis

def format_analysis_text_for_pdf(analysis):
    """Converts Markdown-like formatting in analysis text to HTML that ReportLab can render."""
    # Replace **bold** with <b>bold</b>
    formatted_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', analysis)

    # Replace ``` blocks with a placeholder, to be processed separately for code style
    formatted_text = formatted_text.replace('```', '[CODE_BLOCK]')
    
    return formatted_text

def generate_pdf_report(code, metrics, analysis, output_file):
    # Preprocess the analysis text for bold and code block formatting
    formatted_analysis = format_analysis_text_for_pdf(analysis)

    # Create a PDF document
    doc = SimpleDocTemplate(output_file, pagesize=letter)
    elements = []

    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Title'], alignment=1, fontSize=18)
    heading_style = ParagraphStyle('HeadingStyle', parent=styles['Heading2'], spaceAfter=12)
    subheading_style = ParagraphStyle('SubheadingStyle', parent=styles['Heading3'], spaceAfter=8)
    code_style = ParagraphStyle('CodeStyle', fontName='Courier', fontSize=10, leading=12, spaceBefore=5, spaceAfter=5)
    bullet_style = ParagraphStyle('BulletStyle', parent=styles['BodyText'], bulletIndent=20, spaceBefore=3, leftIndent=20)  # Added leftIndent
    normal_style = styles['BodyText']

    # Add a title
    elements.append(Paragraph("Code Analysis Report", title_style))
    elements.append(Spacer(1, 12))

    # Add original code
    elements.append(Paragraph("Analyzed Code:", heading_style))
    code_lines = code.splitlines()
    for line in code_lines:
        elements.append(Paragraph(f"<pre>{line}</pre>", code_style))
    elements.append(Spacer(1, 12))

    # Add static metrics
    elements.append(Paragraph("Static Code Metrics:", heading_style))
    static_metrics = metrics.get("static_metrics", {})
    table_data = [["Metric", "Value"]]

    for metric, value in static_metrics.items():
        if isinstance(value, dict):  # Handle nested dictionaries for Halstead metrics
            for sub_metric, sub_value in value.items():
                table_data.append([f"{metric} - {sub_metric}", sub_value])
        else:
            table_data.append([metric, value])
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    elements.append(table)
    elements.append(Spacer(1, 12))

    # Add intermediate metrics
    elements.append(Paragraph("McCall's Intermediate Quality Metrics:", heading_style))
    intermediate_metrics = metrics.get("intermediate_level_metrics", {})
    table_data = [["Metric", "Value"]]

    for metric, value in intermediate_metrics.items():
        table_data.append([metric, round(value, 2)])

    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    elements.append(table)

    # Add GPT analysis with proper formatting
    elements.append(Paragraph("GPT Analysis Report:", heading_style))
    analysis_lines = formatted_analysis.split('[CODE_BLOCK]')
    code_block_toggle = False

    for line in analysis_lines:
        if code_block_toggle:
            code_lines_in_block = line.strip().splitlines()
            for code_line in code_lines_in_block:
                elements.append(Paragraph(code_line, code_style))
            elements.append(Spacer(1, 6))
        else:
            # Process regular text with normal styles
            sub_lines = line.splitlines()
            for sub_line in sub_lines:
                if sub_line.startswith("## "):  # Main headings
                    elements.append(Paragraph(sub_line[3:], heading_style))
                elif sub_line.startswith("### "):  # Subheadings
                    elements.append(Paragraph(sub_line[4:], subheading_style))
                elif sub_line.startswith("#### "):  # Sub-subheadings
                    elements.append(Paragraph(sub_line[5:], styles['Heading4']))
                elif sub_line.startswith("- "):  # Bullet points
                    elements.append(Paragraph(sub_line, bullet_style))  # Bullet points with indentation
                else:  # Regular text
                    elements.append(Paragraph(sub_line, normal_style))
        
        # Toggle code block mode for the next section
        code_block_toggle = not code_block_toggle

    elements.append(Spacer(1, 12))

    # Build the PDF
    doc.build(elements)
    print(f"PDF report saved to {output_file}")


def main():
    # Load code and metrics
    if len(sys.argv) != 2:
        print("Usage: python3 pdfreport.py <code_file>")
        sys.exit(1)

    code_file = sys.argv[1]
    metrics_file = f'{code_file[:-3]}_metrics.json'  # Replace with your metrics JSON file path


    with open(code_file, 'r', encoding='utf-8') as f:
        code = f.read()

    # Run the code_metrics_integrated.py program to generate metrics
    result = os.system(f"python3 code_metrics_integrated.py {code_file}")
    if result != 0:
        print("Error running code_metrics_integrated.py")
        sys.exit(1)

    # Check if the metrics file exists before trying to open it
    if not os.path.exists(metrics_file):
        print(f"Metrics file {metrics_file} does not exist.")
        sys.exit(1)

    # Load the generated metrics JSON file
    with open(metrics_file, 'r', encoding='utf-8') as f:
        metrics = json.load(f)
    
    analysis = send_to_gpt_for_analysis(code, metrics)

    # Print analysis and optionally save to a file
    print("GPT Analysis Report:")
    print(analysis)

    # Save analysis to a text file
    
    with open(f"{code_file[:3]}_gpt_analysis_report.txt", "w", encoding="utf-8") as f:
        f.write(analysis)
    print("Analysis report saved to gpt_analysis_report.txt")


    # Generate PDF report
    output_file = f'{code_file[:-3]}_code_analysis_report.pdf'
    generate_pdf_report(code, metrics, analysis, output_file)


    
            # Ensure the GPT_analysis directory exists
    os.makedirs('Metrics_jsons', exist_ok=True)

    # Move the analysis report to the GPT_analysis directory
    analysis_report_path = f"Metrics_jsons/{code_file[:-3]}_metrics.json"
    os.rename(f"{code_file[:-3]}_metrics.json", analysis_report_path)
    print(f"Analysis report moved to {analysis_report_path}")

        # Ensure the GPT_analysis directory exists
    os.makedirs('GPT_analysis', exist_ok=True)

    # Move the analysis report to the GPT_analysis directory
    analysis_report_path = f"GPT_analysis/{code_file[:3]}_gpt_analysis_report.txt"
    os.rename(f"{code_file[:3]}_gpt_analysis_report.txt", analysis_report_path)
    print(f"Analysis report moved to {analysis_report_path}")

        # Ensure the GPT_analysis directory exists
    os.makedirs('PDF_reports', exist_ok=True)

    # Move the analysis report to the GPT_analysis directory
    analysis_report_path = f"PDF_reports/{code_file[:-3]}_code_analysis_report.pdf"
    os.rename(f"{code_file[:-3]}_code_analysis_report.pdf", analysis_report_path)
    print(f"Analysis report moved to {analysis_report_path}")

    
if __name__ == "__main__":
    main()
