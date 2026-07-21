from celery import chain, group

from app.tasks.run_slither import run_slither
from app.tasks.run_fuzzer import run_fuzzer
from app.tasks.run_llm_audit import run_llm_audit
from app.tasks.generate_report import generate_report
from app.tasks.process_upload import process_upload


def build_analysis_pipeline(project_id: int):
    return chain(run_slither.si(project_id))


def build_fuzz_pipeline(project_id: int):
    return chain(run_fuzzer.si(project_id))


def build_llm_audit_pipeline(project_id: int):
    return chain(run_llm_audit.si(project_id))


def build_report_pipeline(project_id: int, output_format: str):
    return chain(generate_report.si(project_id, output_format))


def build_parallel_analysis_pipeline(project_id: int):
    return group(
        run_slither.si(project_id),
        run_fuzzer.si(project_id),
        run_llm_audit.si(project_id),
    )
