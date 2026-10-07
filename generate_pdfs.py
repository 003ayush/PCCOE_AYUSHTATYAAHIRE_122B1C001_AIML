import os
from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 14)
        self.cell(0, 10, 'TATA TECHNOLOGIES LTD.', align='C', new_x="LMARGIN", new_y="NEXT")
        self.set_font('helvetica', 'B', 12)
        self.cell(0, 10, 'TECH PULSE FY-26 | AI/ML Capstone Project', align='C', new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def section_title(self, title):
        self.set_font('helvetica', 'B', 12)
        self.set_text_color(0, 51, 102)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.set_font('helvetica', '', 11)

    def field_pair(self, label, value):
        self.set_font('helvetica', 'B', 10)
        self.cell(50, 8, label)
        self.set_font('helvetica', '', 10)
        self.multi_cell(0, 8, value)
        self.ln(2)

    def bullet(self, text):
        self.set_font('helvetica', '', 10)
        self.multi_cell(0, 6, f"- {text}")
        self.ln(2)

def generate_synopsis(output_path):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 16)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 10, 'PROJECT SYNOPSIS', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)

    pdf.section_title("Student Details")
    pdf.field_pair("Institute/University:", "Pimpri Chinchwad College of Engineering (PCCOE)")
    pdf.field_pair("Programme / Batch:", "CS / AIML")
    pdf.field_pair("Student Name:", "Ayush Tatya Ahire")
    pdf.field_pair("PRN:", "122B1C001")
    pdf.ln(5)

    pdf.section_title("1. Case Study ID and Project Title / Topic")
    pdf.field_pair("Case Study ID:", "CS3 (Automotive Cybersecurity)")
    pdf.field_pair("Project Title / Topic:", "Automotive Cybersecurity TARA Assistant")
    pdf.ln(5)

    pdf.section_title("2. Objectives")
    pdf.bullet("Implement an AI-assisted Threat Analysis and Risk Assessment (TARA) tool conforming to ISO/SAE 21434.")
    pdf.bullet("Automate asset extraction and threat scenario generation using Large Language Models (Mistral/Groq).")
    pdf.bullet("Ground LLM outputs using a deterministic RAG pipeline backed by a UN R155 regulatory threat library.")
    pdf.bullet("Evaluate risks using a standardized risk matrix and trace mitigations directly to threats.")
    pdf.ln(5)

    pdf.section_title("3. Scope")
    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 8, "In Scope - To Be Implemented", ln=True)
    pdf.bullet("Architecture JSON parsing and trust boundary mapping.")
    pdf.bullet("RAG-based threat and mitigation retrieval using ChromaDB.")
    pdf.bullet("FastAPI backend serving LLM integration with fallback chains (Mistral -> Groq).")
    pdf.bullet("Human-in-the-loop review UI via Streamlit.")
    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 8, "Out of Scope - Will Not Be Implemented", ln=True)
    pdf.bullet("Direct execution of penetration tests or automated code scanning.")
    pdf.bullet("Live vehicle telemetry ingestion or active monitoring.")
    pdf.bullet("Non-regulatory threat libraries not specified in UN R155.")
    pdf.ln(5)

    pdf.add_page()
    pdf.section_title("4. Proposed Approach")
    pdf.field_pair("Pre-trained model:", "Mistral (mistral-small-latest) / Groq LLaMA-3 (fallback)")
    pdf.field_pair("Embedding model:", "BAAI/bge-small-en-v1.5 (or dummy hash for local dev)")
    pdf.field_pair("Vector store:", "ChromaDB")
    pdf.field_pair("RAG pipeline:", "LangGraph state machine orchestrating 'Knowledge' and 'Analyst' nodes.")
    pdf.field_pair("Service layer and UI:", "FastAPI (Backend) / Streamlit (Frontend)")
    pdf.field_pair("Tools / rules:", "Strict JSON schema enforcement via Pydantic; deterministic risk computation via 5x5 matrix.")
    pdf.ln(5)

    pdf.section_title("5. Input Data / Knowledge Base")
    pdf.field_pair("Data / Knowledge Sources:", "JSON architecture files, UN R155 threat library, asset catalogue.")
    pdf.field_pair("Approximate Size/Format:", "JSON arrays (~3000 lines, <1MB).")
    pdf.field_pair("Preprocessing and EDA:", "Flattening interfaces, mapping STRIDE categories, mapping trust boundaries.")
    pdf.ln(5)

    pdf.section_title("6. Expected Outcomes and Evaluation Plan")
    pdf.field_pair("Expected Outputs:", "A fully traceable TARA report in Markdown with assets, threats, risks, and mitigations.")
    pdf.field_pair("Evaluation Method:", "Human review pass/fail metrics; Traceability gaps metric.")
    pdf.field_pair("Responsible AI Measures:", "All AI drafts require explicit human approval via the UI. Strict RAG citations.")
    pdf.field_pair("MLOps / Deployment:", "FastAPI backend, standalone execution via run.bat.")
    pdf.ln(5)

    pdf.section_title("7. Planned AI-Tool Usage")
    pdf.field_pair("AI Tool / Model:", "Gemini / Antigravity AI")
    pdf.field_pair("Purpose:", "Coding assistance, architecture migration, debugging.")
    pdf.field_pair("Artifact Affected:", "Codebase and documentation.")
    
    pdf.output(output_path)


def generate_technical_report(output_path):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('helvetica', 'B', 16)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 10, 'TECHNICAL REPORT', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)

    pdf.section_title("1. Problem Statement and Intended Users")
    pdf.set_font('helvetica', '', 10)
    pdf.multi_cell(0, 6, "Threat Analysis and Risk Assessment (TARA) is a highly manual, time-consuming process. The intended users are automotive cybersecurity engineers who require an AI assistant to accelerate ISO/SAE 21434 compliance without compromising on deterministic regulatory grounding.")
    pdf.ln(5)

    pdf.section_title("2. Input Data / Knowledge Base")
    pdf.field_pair("Sources:", "UN R155 Threat library JSON, TCU Architecture JSON.")
    pdf.field_pair("Size and format:", "Structured JSON, small dataset (<1MB).")
    pdf.field_pair("Preprocessing:", "Loaded directly into RAG Store (ChromaDB) on application startup.")
    pdf.field_pair("Chunking strategy:", "Whole record mapping (each threat pattern is an independent document).")
    pdf.ln(5)

    pdf.section_title("3. Solution Architecture")
    pdf.field_pair("Pre-trained model:", "mistral-small-latest (Primary) / Groq LLaMA-3 (Fallback)")
    pdf.field_pair("Embedding model:", "BAAI/bge-small-en-v1.5")
    pdf.field_pair("Vector store:", "ChromaDB")
    pdf.field_pair("RAG pipeline:", "LangGraph nodes separating retrieval (Knowledge) and generation (Analyst).")
    pdf.field_pair("Service layer and UI:", "FastAPI, Streamlit.")
    pdf.field_pair("Tools / rules:", "Python, Pydantic, HTTPX.")
    pdf.ln(5)

    pdf.add_page()
    pdf.section_title("4. Implementation and Configuration")
    pdf.set_font('helvetica', '', 10)
    pdf.multi_cell(0, 6, "Workflow: Ingestion of JSON via API -> Retrieval from ChromaDB using exact match and similarity -> Generation via LangGraph node calling Mistral -> Response strictly validated via Pydantic schemas. Chunk size = whole documents, top_k = 5, temperature = default (0 for deterministic).")
    pdf.ln(5)

    pdf.section_title("5. Evaluation Steps and Results")
    pdf.field_pair("Test 1:", "Upload JSON -> Parses correctly (Pass).")
    pdf.field_pair("Test 2:", "LLM format enforcement -> Drafts exactly match Pydantic schemas (Pass).")
    pdf.field_pair("Test 3:", "Traceability -> Report shows correct gaps and links (Pass).")
    pdf.ln(5)

    pdf.section_title("6. Responsible AI Measures")
    pdf.field_pair("Grounding and citations:", "All items enforce source_ids from RAG. Uncited items are flagged.")
    pdf.field_pair("Privacy / Security:", "Only synthetic TCU architecture data used. Local execution, no internet facing interfaces.")
    pdf.field_pair("Human oversight:", "Needs Expert Review statuses; manual approval required before final report generation.")
    pdf.ln(5)

    pdf.section_title("7. Innovation Highlights")
    pdf.bullet("Deterministic RAG separation from LLM reasoning.")
    pdf.bullet("Fallback chain provider failover (Mistral -> Groq) to ensure high availability.")
    pdf.bullet("Traceability graph reporting for full ISO/SAE 21434 compliance mapping.")
    
    pdf.output(output_path)

if __name__ == '__main__':
    base_dir = r"c:\Users\LEGION\Documents\TATA\PCCOE_StudentName_PRN_CSx_AIML"
    synopsis_path = os.path.join(base_dir, "Synopsis", "Project_Synopsis.pdf")
    tech_report_path = os.path.join(base_dir, "Documentation", "Technical_Report.pdf")
    
    generate_synopsis(synopsis_path)
    generate_technical_report(tech_report_path)
    print(f"Generated {synopsis_path}")
    print(f"Generated {tech_report_path}")
