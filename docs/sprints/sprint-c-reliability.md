# Sprint C: Reliability & Quality Improvements Design Document

## Executive Summary

Sprint C focuses on addressing the remaining MEDIUM and LOW severity vulnerabilities identified in SolidGuard's security audit. This sprint aims to improve code quality, operational readiness, and system reliability through targeted remediation of specific issues while maintaining backward compatibility and minimizing risk to the existing system.

## Sprint Overview

- **Duration:** 1.5 weeks (7.5 developer-days)
- **Theme:** "Polish & Perfect"
- **Goal:** Resolve remaining MEDIUM/LOW vulnerabilities, improve code quality and operational readiness
- **Dependencies:** Sprint 0-7 completed successfully

## Vulnerability Remediation Details

### 16. MEDIUM - Celery task exception handling broken

**What to fix:**
In `backend/app/tasks/process_upload.py`, the exception handling block that uses `str(Exception)` instead of `str(e)` to capture error information.

**How to fix:**
1. Modify the `except` clause to capture the exception variable: `except Exception as e:`
2. Use `str(e)` to extract the actual error message
3. Log the full traceback using `traceback.format_exc()` for debugging
4. Return structured error information in task results instead of generic string
5. Implement proper error categorization (transient vs permanent errors)

**Dependencies:**
None - standalone fix

**Acceptance criteria:**
1. When a Celery task fails, error messages contain specific exception details
2. Task results include error type, message, and optional traceback
3. System logs contain sufficient information for debugging
4. Unit tests verify error handling behavior

**Estimated effort:** 0.5 developer-days

---

### 17. MEDIUM - LLM response JSON parsing fragile

**What to fix:**
In `backend/app/services/engine/llm_audit.py`, the function that extracts JSON from LLM responses using fragile regex patterns.

**How to fix:**
1. Implement a multi-stage JSON extraction pipeline:
   - First attempt: Direct `json.loads()` on trimmed response
   - Second attempt: Extract JSON from markdown code blocks (```json ... ```)
   - Third attempt: Extract JSON arrays/objects using balanced bracket parsing
   - Fourth attempt: Fix common JSON formatting issues (missing quotes, trailing commas)
2. Add response validation schema for expected JSON structure
3. Implement fallback to original response if all parsing attempts fail
4. Add logging for parsing failures with original response for debugging

**Dependencies:**
May share parsing logic with vulnerability 18 (polish_with_llm)

**Acceptance criteria:**
1. LLM responses containing JSON in various formats are parsed correctly
2. Markdown-wrapped JSON is properly extracted
3. Multiple JSON arrays in response are handled appropriately
4. Invalid JSON triggers appropriate error handling without system crash
5. Unit tests cover edge cases in JSON parsing

**Estimated effort:** 1 developer-day

---

### 18. MEDIUM - `polish_with_llm` trusts LLM output

**What to fix:**
In `backend/app/services/report_generator.py`, the `polish_with_llm` function that directly uses `json.loads` on LLM output without validation.

**How to fix:**
1. Implement JSON schema validation for polished output:
   - Define strict schema matching expected audit finding structure
   - Validate severity ratings against allowed values
   - Ensure required fields are present
2. Add content sanitization:
   - Remove potential script injection
   - Validate string lengths and formats
   - Check for unexpected data types
3. Implement diff comparison between original and polished findings:
   - Alert if severity ratings change
   - Flag unexpected structural changes
   - Log all modifications for audit trail
4. Add option to bypass LLM polishing with configuration flag

**Dependencies:**
May share JSON parsing logic with vulnerability 17

**Acceptance criteria:**
1. Polished output passes schema validation
2. Severity ratings remain unchanged unless explicitly allowed
3. Malicious JSON injection is prevented
4. System logs document all changes made by LLM
5. Unit tests verify validation logic

**Estimated effort:** 1 developer-day

---

### 19. MEDIUM - State machine has no DB-level constraints

**What to fix:**
In `backend/app/state/project_state.py`, the state transition logic relying solely on Python checks without database constraints.

**How to fix:**
1. Add database-level constraints:
   - Add CHECK constraint on state column for allowed values
   - Add valid_transitions table or matrix
   - Implement trigger function for state transition validation
2. Implement optimistic locking:
   - Add version column to project table
   - Include version in UPDATE WHERE clause
   - Handle version conflict exceptions
3. Create Alembic migration script:
   - Add new columns and constraints
   - Create validation functions
   - Add indexes for performance
4. Update application code:
   - Modify state transition logic to use database constraints
   - Add proper exception handling for constraint violations
   - Implement retry logic for race conditions

**Dependencies:**
Requires database schema changes and migration scripts

**Acceptance criteria:**
1. Invalid state transitions are rejected at database level
2. Race conditions are handled with optimistic locking
3. Database migration runs without data loss
4. Performance impact is minimal (< 5% increase in query time)
5. Unit and integration tests verify constraint enforcement

**Estimated effort:** 1.5 developer-days

---

### 20. LOW - `__pycache__` and `.pyc` files in version control

**What to fix:**
Remove all `__pycache__/` directories and `.pyc` files from the repository and prevent future additions.

**How to fix:**
1. Remove existing files from version control:
   - Use `git rm -r --cached '**/__pycache__'` and `git rm --cached '**/*.pyc'`
   - Commit removal changes
2. Update `.gitignore` file:
   - Add `__pycache__/` pattern
   - Add `*.pyc` pattern
   - Add `*.pyo` pattern
   - Add `*.pyd` pattern (Windows)
3. Update CI/CD pipeline:
   - Add check to prevent .pyc file commits
   - Fail builds if .pyc files detected

**Dependencies:**
None - standalone fix

**Acceptance criteria:**
1. Repository contains no __pycache__ or .pyc files
2. .gitignore properly excludes Python bytecode files
3. CI pipeline rejects commits containing .pyc files
4. All developers can clone repository without issues

**Estimated effort:** 0.5 developer-days

---

### 21. LOW - Dead code `models_old.py`

**What to fix:**
The file `backend/app/models_old.py` (6285 bytes) and any references to it.

**How to fix:**
1. Conduct code search for imports and references:
   - Search for `from app.models_old import` or `import models_old`
   - Check configuration files for references
   - Review test files for usage
2. If no active dependencies found:
   - Delete the file
   - Remove any empty __init__.py modules that become orphaned
3. If dependencies exist:
   - Migrate code to use current models
   - Update imports accordingly
   - Remove deprecated functionality
4. Update documentation to reflect removal

**Dependencies:**
None - standalone fix

**Acceptance criteria:**
1. models_old.py file is removed from repository
2. No import errors in application
3. All tests continue to pass
4. No references to removed file in codebase

**Estimated effort:** 0.5 developer-days

---

### 22. LOW - Incomplete health check

**What to fix:**
In `backend/app/main.py`, the `/health` endpoint that only checks PostgreSQL via SELECT 1.

**How to fix:**
1. Extend health check to include all dependencies:
   - PostgreSQL: Existing SELECT 1 check
   - Redis: PING command via redis-py client
   - ChromaDB: Simple collection list operation
   - LLM API: Lightweight model listing or status endpoint
2. Implement structured health response:
   - Return JSON with status for each component
   - Include response times for each check
   - Add overall status (healthy/degraded/unhealthy)
3. Add caching for health checks:
   - Cache results for 30 seconds to prevent overload
   - Include cache timestamp in response
4. Implement separate readiness and liveness probes:
   - Liveness: Basic application responsiveness
   - Readiness: All dependencies available

**Dependencies:**
May require adding new client dependencies for health checks

**Acceptance criteria:**
1. `/health` endpoint returns status for all dependencies
2. Response includes component-wise status and response times
3. Health checks complete within 2 seconds timeout
4. Cached results prevent excessive dependency checks
5. Unit tests verify all dependency checks

**Estimated effort:** 1 developer-day

---

### 23. LOW - Docker image layers contain root-owned files

**What to fix:**
In `docker/Dockerfile`, build steps that leave root-owned files despite final USER appuser.

**How to fix:**
1. Restructure Dockerfile using multi-stage builds:
   - Build stage: Install dependencies as root
   - Final stage: Copy artifacts and set ownership
2. Use --chown flag in COPY commands:
   - `COPY --chown=appuser:appuser . /app`
3. Modify package installation:
   - Install Python packages to user directory: `pip install --user`
   - Set virtual environment ownership during creation
4. Clean up root-owned files:
   - Add `RUN chown -R appuser:appuser /app` before USER switch
   - Remove unnecessary build artifacts

**Dependencies:**
None - standalone fix

**Acceptance criteria:**
1. Final Docker image contains no root-owned files in application directory
2. `ls -la` shows all files owned by appuser
3. Image size does not increase significantly (< 5%)
4. Application functions correctly with new file ownership

**Estimated effort:** 1 developer-day

---

### 24. LOW - No graceful shutdown

**What to fix:**
Configuration for FastAPI and Celery workers regarding shutdown behavior.

**How to fix:**
1. Implement FastAPI graceful shutdown:
   - Register shutdown event handler: `@app.on_event("shutdown")`
   - Close database connections in handler
   - Stop accepting new requests
   - Wait for in-progress requests to complete
2. Configure Celery worker shutdown:
   - Set `CELERYD_MAX_TASKS_PER_CHILD` to prevent memory leaks
   - Implement worker shutdown signal handlers
   - Use `--max-tasks-per-child` option
3. Add Docker stop signal handling:
   - Use `STOPSIGNAL SIGTERM` in Dockerfile
   - Configure reasonable stop timeout (30 seconds)
   - Implement health check for graceful shutdown status
4. Add monitoring:
   - Log shutdown initiation and completion
   - Track active tasks during shutdown
   - Monitor for connection leaks

**Dependencies:**
May relate to overall application stability and resource management

**Acceptance criteria:**
1. FastAPI waits for in-progress requests to complete on shutdown
2. Celery workers complete current tasks before exiting
3. Database connections are properly closed
4. Rolling updates do not interrupt user requests
5. Shutdown logs indicate successful cleanup

**Estimated effort:** 1 developer-day

---

## Sprint-level Risk Assessment

### High Risk

1. **Database migration for state constraints (Vulnerability 19)**
   - Risk: Downtime or data integrity issues if migration fails
   - Mitigation:
     - Test migration on staging environment with production data clone
     - Create rollback migration script
     - Schedule migration during low-traffic window
     - Have database backup ready before migration

2. **LLM parsing changes (Vulnerabilities 17 & 18)**
   - Risk: Changes might affect audit accuracy or break existing functionality
   - Mitigation:
     - Implement feature flags for gradual rollout
     - A/B test new parsing logic against current implementation
     - Monitor audit quality metrics post-deployment

### Medium Risk

1. **Docker image restructuring (Vulnerability 23)**
   - Risk: Application fails to start due to permission issues
   - Mitigation:
     - Test new image in staging environment
     - Verify all file access patterns work with new ownership
     - Keep previous image version for quick rollback

2. **Graceful shutdown implementation (Vulnerability 24)**
   - Risk: Incomplete shutdown causes resource leaks
   - Mitigation:
     - Implement comprehensive logging for shutdown process
     - Add monitoring for connection pool usage
     - Test shutdown under load conditions

### Low Risk

1. **File cleanup (Vulnerabilities 20 & 21)**
   - Risk: Minimal - removing unused files
   - Mitigation: Verify no hidden dependencies before removal

2. **Health check expansion (Vulnerability 22)**
   - Risk: Health check endpoint becomes too slow
   - Mitigation: Implement caching and timeouts

---

## Rollback Strategy

### Immediate Rollback (within 30 minutes)

1. **Code Rollback:**
   - Use git revert for specific commits
   - Redeploy previous Docker image version
   - Rollback database migration if needed

2. **Database Rollback:**
   - Execute rollback migration script
   - Restore from backup if data corruption detected
   - Switch to read-only mode during recovery

### Gradual Rollback (within 2 hours)

1. **Feature Flags:**
   - Disable specific features via configuration
   - Use A/B testing framework to route traffic to previous version

2. **Monitoring-Based Rollback:**
   - Set up alerts for error rate increases
   - Define rollback triggers (e.g., > 5% error rate increase)
   - Automate rollback based on health metrics

### Full Rollback (within 4 hours)

1. **Complete Environment Restore:**
   - Restore entire environment from backup
   - Revert all configuration changes
   - Communicate maintenance window to users

---

## Overall Sprint C Acceptance Criteria

### Functional Requirements

1. All MEDIUM vulnerabilities (16-19) are addressed and closed
2. All LOW vulnerabilities (20-24) are addressed and closed
3. No regression in existing functionality
4. All unit and integration tests pass
5. Code coverage remains above 80%

### Non-Functional Requirements

1. **Performance:**
   - Health check endpoint responds within 2 seconds
   - Database queries show < 5% performance degradation
   - Docker image size increases by < 5%

2. **Reliability:**
   - System handles concurrent state transitions correctly
   - Graceful shutdown works under load
   - Error messages provide sufficient debugging information

3. **Security:**
   - No new security vulnerabilities introduced
   - LLM output properly validated and sanitized
   - Database constraints prevent invalid state transitions

4. **Operational Readiness:**
   - Comprehensive health checks for all dependencies
   - Proper logging for debugging and monitoring
   - Documentation updated for all changes

### Verification Process

1. **Automated Testing:**
   - Unit tests for all modified functions
   - Integration tests for database constraints
   - End-to-end tests for state machine transitions

2. **Manual Testing:**
   - Verify error handling with invalid inputs
   - Test graceful shutdown scenarios
   - Validate Docker image in staging environment

3. **Security Review:**
   - Code review for all changes
   - Static analysis scan
   - Penetration testing for new validation logic

---

## Sprint Planning

### Week 1 (5 days)

- **Days 1-2:** Database migration and state machine constraints (Vulnerability 19)
- **Days 3-4:** LLM parsing improvements (Vulnerabilities 17 & 18)
- **Day 5:** Celery error handling and health checks (Vulnerabilities 16 & 22)

### Week 2 (2.5 days)

- **Days 6-7:** Docker image restructuring and graceful shutdown (Vulnerabilities 23 & 24)
- **Day 7.5 (half day):** Repository cleanup - remove __pycache__, dead code, update .gitignore (Vulnerabilities 20 & 21)
- **Buffer:** Regression testing and final integration verification

### Key Milestones

- **Day 2:** State machine constraints deployed with database migration
- **Day 4:** LLM parsing improvements validated with test suite
- **Day 5:** All MEDIUM vulnerabilities closed
- **Day 7:** All LOW vulnerabilities closed
- **Day 7.5:** Sprint C complete, all 25 vulnerabilities remediated

---

**Document Version:** 1.0
**Generated by:** MetaGPT Architect (Bob) via mimo-v2.5-pro
**Date:** 2026-06-09
