from app.services.engine.base import BaseEngine
from app.services.report_generator import (
    aggregate_findings,
    generate_html,
    generate_pdf,
    generate_word,
    polish_with_llm,
)


class ReportEngine(BaseEngine):
    def execute(self, project_id: int, output_format: str, session) -> dict:
        raw_findings = aggregate_findings(project_id, session)

        polished_findings = polish_with_llm(raw_findings)

        title = f"SolidiGuard Audit Report - Project {project_id}"

        file_paths = {}

        if output_format == "html":
            html_path = generate_html(project_id, title, polished_findings)
            file_paths["html"] = html_path
        elif output_format == "pdf":
            html_path = generate_html(project_id, title, polished_findings)
            pdf_path = generate_pdf(html_path)
            file_paths["html"] = html_path
            file_paths["pdf"] = pdf_path
        elif output_format == "word":
            docx_path = generate_word(polished_findings, title, project_id)
            file_paths["word"] = docx_path

        report_content = {
            "raw_findings": raw_findings,
            "polished_findings": polished_findings,
        }

        total_findings = (
            len(raw_findings.get("slither_findings", []))
            + len(raw_findings.get("fuzzing_findings", []))
            + len(raw_findings.get("llm_findings", []))
        )

        return {
            "file_paths": file_paths,
            "title": title,
            "total_findings": total_findings,
            "report_content": report_content,
        }
