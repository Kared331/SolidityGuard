# Sprint A: Security Critical Remediation Design Document

**Project:** SolidGuard - Enterprise Solidity Smart Contract Audit Platform  
**Sprint Duration:** 2 Weeks  
**Theme:** "Secure the Perimeter"  
**Goal:** Eliminate all CRITICAL vulnerabilities and HIGH security risks

---

## Sprint Overview

This sprint focuses on remediating the 7 identified security vulnerabilities that pose critical risks to the platform's security posture. The vulnerabilities range from path traversal attacks to authentication bypasses and data leakage issues.

## Vulnerability Remediation Design

### 1. CRITICAL - Zip Slip/Tar Slip Bypass

**What to fix:**  
`backend/app/services/engine/upload.py` L36-60 - The `extract_archive` function

**How to fix:**  
- Replace the current extraction approach with a secure extraction method that validates each member's path before extraction
- Implement a strict path validation function that resolves symbolic links and ensures all extracted files remain within the designated extraction directory
- Use Python's `os.path.realpath()` and `os.path.commonpath()` to validate paths
- Extract files individually using `member.extract()` instead of `extractall()` to maintain control
- Add file permission restrictions (read-only) to extracted files
- Implement maximum file size limits and total archive size limits
- Add logging for all extraction attempts with detailed error information

**Dependencies:**  
None - This fix is independent

**Acceptance Criteria:**  
1. Malicious archives with path traversal attempts fail to extract outside the target directory
2. Symbolic link attacks are neutralized
3. Archive extraction functions correctly for legitimate archives
4. Unit tests pass for both malicious and legitimate archives
5. Integration tests verify upload functionality works end-to-end

**Estimated Effort:** 2 developer-days

---

### 2. CRITICAL - SSE Endpoint Bypasses Authentication

**What to fix:**  
`backend/app/api/v1/events.py` + `backend/app/api/router.py` - SSE endpoint authentication

**How to fix:**  
- Modify `events_router` to use the same authentication dependency as other endpoints
- Remove the insecure query parameter-based authentication for SSE endpoints
- Implement WebSocket-based or header-based authentication for SSE connections
- Add connection-level authentication validation
- Implement connection timeout and re-authentication for long-lived SSE connections
- Add rate limiting for SSE connections to prevent abuse
- Ensure proper connection cleanup on authentication failure

**Dependencies:**  
None - This fix is independent

**Acceptance Criteria:**  
1. SSE endpoints require valid authentication headers
2. Connections without valid authentication are rejected with 401 Unauthorized
3. Authenticated SSE connections function correctly for real-time updates
4. Connection limits prevent resource exhaustion attacks
5. Unit and integration tests verify authentication works for SSE

**Estimated Effort:** 1.5 developer-days

---

### 3. CRITICAL - Route Prefix Conflicts Causing 404s

**What to fix:**  
`backend/app/api/router.py` - Route prefix configuration

**How to fix:**  
- Analyze all router registrations and their route definitions
- Remove duplicate prefixes from route definitions where routers already have prefixes
- Standardize the API structure with consistent prefix usage
- Implement a route validation utility that checks for prefix conflicts during startup
- Add health check endpoints that verify all critical routes are accessible
- Implement comprehensive route logging to detect future issues
- Consider API versioning strategy to prevent future conflicts

**Dependencies:**  
None - This fix is independent

**Acceptance Criteria:**  
1. All API endpoints respond with correct status codes (no more 404s for existing endpoints)
2. API endpoints maintain backward compatibility
3. Health check endpoints verify all critical routes
4. Integration tests pass for all affected endpoints
5. Route conflicts are detected during application startup

**Estimated Effort:** 1 developer-day

---

### 4. CRITICAL - Report Download Path Traversal

**What to fix:**  
`backend/app/services/report_service.py` L49-65 - `get_report_download_info` function

**How to fix:**  
- Implement strict path validation for all report file paths
- Validate that all file paths are within the designated reports directory
- Use `os.path.realpath()` and `os.path.commonpath()` to resolve and validate paths
- Add a whitelist of allowed file extensions for reports
- Implement file existence validation before serving
- Add download logging for audit purposes
- Consider implementing signed URLs for report downloads with expiration
- Add rate limiting for download requests

**Dependencies:**  
None - This fix is independent

**Acceptance Criteria:**  
1. Path traversal attempts are blocked with 403 Forbidden
2. Only files within the reports directory can be downloaded
3. Invalid file paths return appropriate error messages
4. Legitimate report downloads function correctly
5. All download attempts are logged for audit

**Estimated Effort:** 1 developer-day

---

### 5. HIGH - LLM Prompt Injection

**What to fix:**  
`backend/app/services/engine/llm_audit.py` - LLM prompt construction

**How to fix:**  
- Implement input sanitization for all Solidity source code before prompt injection
- Use structured prompts with clear delimiters for code sections
- Implement prompt template system with variable escaping
- Add detection for known prompt injection patterns
- Implement a sandboxing mechanism for LLM interactions
- Add input length limits for source code submissions
- Implement prompt response validation to detect when injection attempts succeed
- Consider using multiple LLM models with cross-validation for critical analyses

**Dependencies:**  
None - This fix is independent

**Acceptance Criteria:**  
1. Known prompt injection patterns are detected and blocked
2. LLM responses are validated for consistency
3. Legitimate Solidity code is analyzed correctly
4. Sanitization doesn't affect code analysis quality
5. Unit tests verify injection prevention works

**Estimated Effort:** 2 developer-days

---

### 6. HIGH - Frontend API Key Baked into Build

**What to fix:**  
`frontend/Dockerfile` + `frontend/src/utils/client.ts` - Frontend API key configuration

**How to fix:**  
- Remove the `VITE_API_KEY` from the build process entirely
- Implement a secure API key management system using environment variables at runtime
- Implement an API key rotation mechanism
- Add key expiration and validation
- Consider implementing JWT-based authentication for frontend users
- Implement secure key storage using OS keychain or secrets manager
- Add key usage monitoring and alerting
- Implement key revocation capabilities

**Dependencies:**  
SSE authentication fix (Item 2) should be implemented first to ensure consistent authentication

**Acceptance Criteria:**  
1. No API keys are present in the frontend JavaScript bundle
2. API authentication works using runtime configuration
3. Key rotation can be performed without downtime
4. Compromised keys can be revoked immediately
5. Key usage is monitored and logged

**Estimated Effort:** 2 developer-days

---

### 7. HIGH - False Positive Feedback Has No Project Scope

**What to fix:**  
`backend/app/models/feedback.py` - False Positive feedback model

**How to fix:**  
- Add `project_id` field to the False Positive feedback model
- Create database migration to add the new field
- Update all feedback creation code to include project context
- Implement project-scoped feedback queries
- Add unique constraints to prevent duplicate feedback within projects
- Implement feedback inheritance for shared code across projects
- Add API endpoints for project-specific feedback management
- Implement feedback aggregation and reporting per project

**Dependencies:**  
None - This fix is independent

**Acceptance Criteria:**  
1. False Positive feedback is scoped to projects
2. Cross-project feedback leakage is prevented
3. Existing feedback is migrated with appropriate project context
4. API endpoints provide project-scoped feedback operations
5. Database constraints prevent duplicate feedback within projects

**Estimated Effort:** 1.5 developer-days

---

## Sprint-Level Risk Assessment

### Technical Risks

1. **Regression Risk:** Security fixes may break existing functionality
   - **Mitigation:** Comprehensive test suite, staged rollout, feature flags
   - **Probability:** Medium
   - **Impact:** High

2. **Performance Impact:** Path validation and input sanitization may add latency
   - **Mitigation:** Performance testing, caching, optimized algorithms
   - **Probability:** Low
   - **Impact:** Medium

3. **Integration Issues:** Fixes may interact unexpectedly
   - **Mitigation:** Integration testing, dependency mapping, phased implementation
   - **Probability:** Medium
   - **Impact:** Medium

### Operational Risks

1. **Deployment Complexity:** Multiple security changes increase deployment risk
   - **Mitigation:** Blue-green deployment, automated rollbacks, comprehensive monitoring
   - **Probability:** Medium
   - **Impact:** High

2. **Team Skill Gaps:** Security remediation requires specialized knowledge
   - **Mitigation:** Security training, code reviews, external consultation if needed
   - **Probability:** Low
   - **Impact:** Medium

### Schedule Risks

1. **Scope Creep:** Additional vulnerabilities may be discovered during remediation
   - **Mitigation:** Strict scope control, time-boxed investigation, defer non-critical issues
   - **Probability:** Medium
   - **Impact:** High

2. **Testing Complexity:** Security testing requires additional time and tools
   - **Mitigation:** Automated security testing, parallel test execution, risk-based testing
   - **Probability:** High
   - **Impact:** Medium

## Rollback Strategy

### Immediate Rollback Plan

1. **Database Changes:**
   - All migrations will be reversible with rollback scripts
   - Database backups before each migration step
   - Point-in-time recovery capability maintained

2. **Code Changes:**
   - Feature flags for critical security fixes
   - Version-controlled configuration files
   - Automated rollback scripts for failed deployments

3. **Configuration Changes:**
   - Version-controlled environment configurations
   - Gradual rollout with monitoring
   - Automatic rollback on error thresholds

### Phased Rollback Approach

**Phase 1 (Immediate):**
- Disable affected functionality via feature flags
- Revert to previous code version
- Restore database from backup if needed

**Phase 2 (Short-term):**
- Assess impact of rollback
- Implement temporary workarounds
- Plan forward fix implementation

**Phase 3 (Long-term):**
- Analyze root cause of issues
- Improve testing and validation
- Update rollback procedures

### Monitoring and Alerting

1. **Key Metrics to Monitor:**
   - Error rates for critical endpoints
   - Authentication failure rates
   - File operation success rates
   - Database query performance
   - API response times

2. **Alert Thresholds:**
   - Error rate > 1% for critical paths
   - Authentication failure rate > 5%
   - Response time increase > 50%
   - Database connection pool exhaustion

## Overall Sprint A Acceptance Criteria

### Security Requirements

1. **Zero Critical Vulnerabilities:** No CRITICAL or HIGH security vulnerabilities remain
2. **Security Testing:** All fixes pass automated security scanning
3. **Penetration Testing:** No new vulnerabilities introduced by fixes
4. **Compliance:** Fixes meet OWASP Top 10 and other relevant standards

### Functional Requirements

1. **Backward Compatibility:** All existing functionality continues to work
2. **Performance:** No significant performance degradation (<10% increase in response time)
3. **Reliability:** Error rates remain below established thresholds
4. **Scalability:** System handles current load without issues

### Quality Requirements

1. **Test Coverage:** >90% code coverage for modified code
2. **Documentation:** All changes documented with clear rationale
3. **Code Review:** All changes reviewed by security team member
4. **Monitoring:** All critical paths monitored with appropriate alerts

### Operational Requirements

1. **Deployment:** Successful deployment to staging and production
2. **Rollback:** Rollback capability tested and verified
3. **Monitoring:** All monitoring and alerting systems operational
4. **Documentation:** Runbooks updated for security incident response

---

## Implementation Schedule

### Week 1: Critical Fixes

**Days 1-2:** Route prefix conflicts and authentication bypass fixes  
**Days 3-4:** Path traversal vulnerabilities (upload and download)  
**Day 5:** Integration testing and regression testing for Week 1 fixes

### Week 2: High Priority Fixes

**Days 1-2:** Frontend API key security and LLM prompt injection  
**Days 3-4:** False positive feedback scoping and additional hardening  
**Day 5:** Final integration testing, security scanning, and deployment preparation

### Key Milestones

- **Day 2:** Authentication and routing fixes deployed to staging
- **Day 4:** Path traversal fixes verified with security testing
- **Day 6:** Frontend security and LLM hardening complete
- **Day 8:** All fixes integrated and tested
- **Day 10:** Sprint A complete with all acceptance criteria met

---

## Appendix

### Tools and Libraries

1. **Path Validation:** `os.path.realpath()`, `pathlib` with strict mode
2. **Input Sanitization:** Custom sanitizer with regex patterns
3. **Security Scanning:** Bandit, Safety, OWASP ZAP
4. **Testing:** Pytest, Selenium, Locust for performance testing
5. **Monitoring:** Prometheus, Grafana, ELK stack

### References

1. OWASP Path Traversal Prevention Cheat Sheet
2. OWASP Input Validation Cheat Sheet
3. NIST Secure Software Development Framework
4. Python Security Best Practices

---

**Document Version:** 1.0  
**Last Updated:** 2026-06-09  
**Approved By:** [To be filled]  
**Next Review:** Sprint A Completion Review