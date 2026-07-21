# 馃洝锔?SolidGuard Master Blueprint 鈥?鏋舵瀯婕忔礊淇鎬昏摑鍥?
**椤圭洰锛?* SolidGuard 鈥?浼佷笟绾?Solidity 鏅鸿兘鍚堢害瀹¤骞冲彴
**鎶€鏈爤锛?* FastAPI + Celery + PostgreSQL + Redis + ChromaDB + React + Docker Compose
**褰撳墠鐘舵€侊細** Sprint 0-7 宸插畬鎴愶紝鍏ㄥ姛鑳藉彲鐢紝鍙戠幇 25 椤规灦鏋勬紡娲?**鎬昏摑鍥剧増鏈細** 1.0
**鐢熸垚鏃ユ湡锛?* 2026-06-09
**鐢熸垚宸ュ叿锛?* MetaGPT (Architect Bob) via mimo-v2.5-pro + Claw閰?鏁村悎

---

## 馃搵 Executive Summary

SolidGuard 鏄竴涓紒涓氱骇 Solidity 鏅鸿兘鍚堢害瀹¤骞冲彴锛屽凡瀹屾垚 Sprint 0-7 鐨勫叏閮ㄥ姛鑳藉紑鍙戙€傜粡杩囧叏闈㈢殑鏋舵瀯浠ｇ爜瀹℃煡锛屽叡鍙戠幇 **25 椤规灦鏋勬紡娲?*锛屾兜鐩栧畨鍏ㄣ€佸彲闈犳€с€佽繍缁寸瓑棰嗗煙銆?
### 椋庨櫓姒傚喌
- **4 椤?CRITICAL** 鈥?杩滅▼浠ｇ爜鎵ц銆佽璇佺粫杩囥€佽矾寰勯亶鍘嗘敾鍑?- **6 椤?HIGH** 鈥?鏁版嵁瀹屾暣鎬с€佸畨鍏ㄦ帶鍒躲€佸熀纭€璁炬柦绋冲畾鎬?- **9 椤?MEDIUM** 鈥?鎬ц兘銆佸彲鎵╁睍鎬с€佸彲闈犳€?- **6 椤?LOW** 鈥?鎶€鏈€哄姟銆佽繍缁存晥鐜?
### 淇绛栫暐
閲囩敤 **4 Sprint 娓愯繘寮忎慨澶嶆柟妗?*锛屾寜涓ラ噸鎬у拰渚濊禆鍏崇郴鎺掑簭锛?
| Sprint | 涓婚 | 鍛ㄦ湡 | 宸ヤ綔閲?| 閲嶇偣 |
|--------|------|------|--------|------|
| **A** | 瀹夊叏鍏抽敭淇 | 2 鍛?| 11 澶?| CRITICAL + 瀹夊叏鐩稿叧 HIGH |
| **B** | 鍩虹璁炬柦鍔犲浐 | 2 鍛?| 8.5 澶?| HIGH 鍩虹璁炬柦 + MEDIUM 鎬ц兘 |
| **C** | 鍙潬鎬т笌璐ㄩ噺 | 1.5 鍛?| 7.5 澶?| 鍓╀綑 MEDIUM + LOW |
| **D** | 娴嬭瘯涓庢枃妗?| 1 鍛?| 12 澶?| 娴嬭瘯瑕嗙洊 + 鏂囨。瀹屽杽 |
| **鎬昏** | | **6.5 鍛?* | **39 澶?* | 鍏ㄩ儴 25 椤规紡娲?|

---

## 馃搳 Vulnerability Matrix

| ID | 涓ラ噸鎬?| 缁勪欢 | 鎻忚堪 | Sprint | 宸ヤ綔閲?|
|----|--------|------|------|--------|--------|
| 1 | 馃敶 CRITICAL | `upload.py` L36-60 | Zip Slip/Tar Slip 闃叉姢缁曡繃 | A | 2 澶?|
| 2 | 馃敶 CRITICAL | `events.py` + `router.py` | SSE 绔偣缁曡繃璁よ瘉 | A | 1.5 澶?|
| 3 | 馃敶 CRITICAL | `router.py` | 璺敱鍓嶇紑鍐茬獊瀵艰嚧 404 | A | 1 澶?|
| 4 | 馃敶 CRITICAL | `report_service.py` L49-65 | 鎶ュ憡涓嬭浇璺緞閬嶅巻 | A | 1 澶?|
| 5 | 馃煚 HIGH | `llm_audit.py` | LLM Prompt 娉ㄥ叆 | A | 2 澶?|
| 6 | 馃煚 HIGH | 鎵€鏈夋ā鍨?| 澶栭敭缂哄皯鏁版嵁搴撶储寮?| B | 1 澶?|
| 7 | 馃煚 HIGH | `cleanup.py` | 娓呯悊浠诲姟涓嶅垹闄ゅ叧鑱旇褰?| B | 1 澶?|
| 8 | 馃煚 HIGH | `Dockerfile` + `client.ts` | 鍓嶇 API Key 娉勯湶 | A | 2 澶?|
| 9 | 馃煚 HIGH | `main.py` | 鏃?CORS 閰嶇疆 | B | 0.5 澶?|
| 10 | 馃煚 HIGH | `feedback.py` | FP 鍙嶉鏃犻」鐩綔鐢ㄥ煙 | A | 1.5 澶?|
| 11 | 馃煛 MEDIUM | 鎵€鏈?API 绔偣 | 鏃犻€熺巼闄愬埗 | B | 1 澶?|
| 12 | 馃煛 MEDIUM | `events.py` | SSE 杞閫犳垚鏁版嵁搴撳帇鍔?| B | 2 澶?|
| 13 | 馃煛 MEDIUM | `chroma_client.py` + `embedding.py` | 鍗曚緥闈炵嚎绋嬪畨鍏?| B | 1 澶?|
| 14 | 馃煛 MEDIUM | `embedding.py` | Embedding 妯″瀷鍚嶇‖缂栫爜 | B | 0.5 澶?|
| 15 | 馃煛 MEDIUM | `process_upload.py` | Celery 寮傚父澶勭悊閿欒 | C | 0.5 澶?|
| 16 | 馃煛 MEDIUM | `database.py` | 鏃犳暟鎹簱杩炴帴姹犻厤缃?| B | 0.5 澶?|
| 17 | 馃煛 MEDIUM | `llm_audit.py` | LLM JSON 瑙ｆ瀽鑴嗗急 | C | 1 澶?|
| 18 | 馃煛 MEDIUM | `report_generator.py` | `polish_with_llm` 淇′换 LLM 杈撳嚭 | C | 1 澶?|
| 19 | 馃煛 MEDIUM | `project_state.py` | 鐘舵€佹満鏃?DB 绾︽潫 (TOCTOU) | C | 1.5 澶?|
| 20 | 馃數 LOW | 浠撳簱 | `__pycache__` 鍦ㄧ増鏈帶鍒朵腑 | C | 0.5 澶?|
| 21 | 馃數 LOW | `models_old.py` | 姝讳唬鐮?| C | 0.5 澶?|
| 22 | 馃數 LOW | `main.py` | 鍋ュ悍妫€鏌ヤ笉瀹屾暣 | C | 1 澶?|
| 23 | 馃數 LOW | `Dockerfile` | Docker 灞傚惈 root 鏂囦欢 | C | 1 澶?|
| 24 | 馃數 LOW | `main.py` + Celery | 鏃犱紭闆呭仠鏈?| C | 1 澶?|
| 25 | 馃數 LOW | `tests/` | 娴嬭瘯瑕嗙洊涓嶈冻 | D | 12 澶?|

---

## 馃搻 Dependency Graph

```
Sprint A (CRITICAL) 鈹€鈹€鈫?Sprint B (HIGH) 鈹€鈹€鈫?Sprint C (MEDIUM) 鈹€鈹€鈫?Sprint D (Testing)

Sprint A 鍐呴儴渚濊禆:
  #3 璺敱淇 鈹€鈹€鈫?#2 SSE 璁よ瘉 (璺敱蹇呴』鍏堝瓨鍦?
  #5 杈撳叆楠岃瘉 鈹€鈹€鈫?#16 閿欒澶勭悊

Sprint B 鍐呴儴渚濊禆:
  #6 鏁版嵁搴撶储寮?鈹€鈹€鈫?#12 鏌ヨ浼樺寲
  #9 CORS 鈹€鈹€鈫?鍓嶇闆嗘垚

Sprint C 鍐呴儴渚濊禆:
  #19 鐘舵€佹満 鈹€鈹€鈫?#20 浠诲姟閲嶈瘯 鈹€鈹€鈫?#21 Celery 閰嶇疆

Sprint D 渚濊禆:
  #25 娴嬭瘯瑕嗙洊 (闇€瑕佹墍鏈夊墠缃慨澶嶅畬鎴?

鍏抽敭璺緞:
  #3 鈫?#2 鈫?#19 鈫?#20 鈫?#21 鈫?#25 (绾?3.5 鍛?
```

---

## 馃搮 Timeline Estimate

**鍋囪锛?* 2 鍚嶉珮绾у紑鍙?+ 1 鍚?QA 宸ョ▼甯?
```
Week 1  (Jun 16-20): Sprint A 鈥?瀹夊叏鍏抽敭淇
Week 2  (Jun 23-27): Sprint B 鈥?鍩虹璁炬柦鍔犲浐
Week 3  (Jun 30-Jul 4): Sprint C 鈥?鍙潬鎬т笌璐ㄩ噺
Week 4  (Jul 7-11): Sprint D 鈥?娴嬭瘯涓庢枃妗?Week 5  (Jul 14-18): Buffer / 閮ㄧ讲鍑嗗
```

**璧勬簮鍒嗛厤锛?*
- 寮€鍙?1锛氳矾鐢便€佽璇併€佺姸鎬佹満
- 寮€鍙?2锛氭暟鎹簱銆佹湇鍔°€丆elery
- QA锛氭祴璇曠瓥鐣ャ€佸畨鍏ㄦ祴璇曘€佹枃妗?
**鎴愬姛鎸囨爣锛?*
- 0 椤?CRITICAL/HIGH 婕忔礊鍓╀綑
- 鍏抽敭妯″潡娴嬭瘯瑕嗙洊 >80%
- 鎬ц兘鍩哄噯缁存寔涓嶅彉
- 瀹屾暣鏂囨。闆?- 闆跺仠鏈洪儴缃茶兘鍔?
---

## 馃搧 鍚?Sprint 璇︾粏璁捐

浠ヤ笅鏄悇 Sprint 鐨勫畬鏁磋璁℃枃妗ｏ紝鐢?MetaGPT Architect (Bob) 閫氳繃 mimo-v2.5-pro 鐢熸垚锛?
---

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

---

## Sprint B: 基础设施加固

# Sprint B: Infrastructure Hardening (2 Weeks)

**Goal:** Harden infrastructure, improve performance, establish monitoring.

**Theme:** "Build Resilience"

## Vulnerabilities to Address

### 8. Missing database indexes

- **What to fix:** All models in `backend/app/models/` where foreign keys are defined, such as `project_id`, `analysis_result_id`, etc. The issue is that SQLAlchemy does not automatically create indexes on foreign key columns, leading to slow queries and potential performance bottlenecks.

- **How to fix:** Add explicit indexes to foreign key columns in the SQLAlchemy models. For each model class with a foreign key field, set `index=True` in the column definition or use SQLAlchemy's `Index` construct. This ensures indexes are created during database migrations. Review all models (e.g., `Project`, `AnalysisResult`, `Detection`) to ensure consistency.

- **Dependencies:** This fix is independent but requires database migration updates. Coordinate with any schema changes in other fixes.

- **Acceptance criteria:** After applying indexes and running migrations, verify with database tools (e.g., `EXPLAIN` on common queries involving joins) that foreign key columns are indexed. Performance tests should demonstrate improved query speeds for operations filtering or joining on these columns.

- **Estimated effort:** 1 developer-day.

### 9. Cleanup task doesn't delete related records

- **What to fix:** `backend/app/tasks/cleanup.py` in the `cleanup_old_files` function. Currently, it only deletes `ProjectFile` and `Project` records, leaving orphan `AnalysisResult`, `Detection`, `FuzzingResult`, `LLMAuditResult`, and `Report` records, which accumulate and waste storage.

- **How to fix:** Implement cascade deletion logic in the cleanup task. Update the task to query and delete all related records before deleting the project, or leverage SQLAlchemy relationships with `cascade="all, delete-orphan"` in model definitions to automate this. Ensure that deletions are atomic to maintain data integrity.

- **Dependencies:** Depends on proper relationship definitions in models; if relationships are not set, model adjustments may be needed. This fix should be coordinated with database index changes to optimize deletion performance.

- **Acceptance criteria:** Run the cleanup task on a test database with orphan records and verify that all related records are deleted. No orphan records should remain, and the task should complete without errors.

- **Estimated effort:** 1 developer-day.

### 10. No CORS configuration

- **What to fix:** `backend/app/main.py` where the FastAPI app is created. No Cross-Origin Resource Sharing (CORS) middleware is configured, blocking frontend-backend communication in development due to browser security policies.

- **How to fix:** Add FastAPI's `CORSMiddleware` to the app. Configure allowed origins for development (e.g., `http://localhost:5173`) and production using environment variables. Set appropriate methods (e.g., GET, POST), headers, and credentials as required.

- **Dependencies:** Independent of other fixes.

- **Acceptance criteria:** From the frontend running on `localhost:5173`, make API requests to the backend on `localhost:8000` and verify no CORS errors occur. Check response headers for `Access-Control-Allow-Origin` matching the expected origin.

- **Estimated effort:** 0.5 developer-days.

### 11. No rate limiting

- **What to fix:** All API endpoints in `backend/app/api/v1/`. No rate limiting is implemented, exposing the system to brute-force attacks and excessive resource consumption.

- **How to fix:** Integrate a rate limiting library such as `slowapi` for FastAPI. Define rate limits per endpoint or globally, such as limiting requests per IP address or per user. Use Redis for distributed rate limiting if needed. Configure limits to mitigate risks like brute-forcing project IDs or triggering excessive LLM audit tasks.

- **Dependencies:** Requires Redis, which is already in the stack. Should be implemented after CORS to ensure rate limiting headers are properly handled.

- **Acceptance criteria:** Test by sending excessive requests to an endpoint (e.g., using a script) and verify that after exceeding the limit, responses return HTTP 429 Too Many Requests. Monitor logs or metrics to confirm rate limiting is active.

- **Estimated effort:** 1 developer-day.

### 12. SSE polling causes database pressure

- **What to fix:** `backend/app/api/v1/events.py` where Server-Sent Events (SSE) are handled. Clients poll the database every second with COUNT queries, leading to high queries per second (QPS) and unnecessary database load.

- **How to fix:** Redesign the SSE mechanism to use a pub/sub system like Redis for real-time updates. When events occur (e.g., analysis completion), publish messages to Redis channels. SSE endpoints subscribe to these channels and stream updates to clients without querying the database repeatedly, reducing database pressure.

- **Dependencies:** Requires Redis, which is already available. May involve refactoring event handling logic across the codebase.

- **Acceptance criteria:** With multiple SSE clients connected, monitor database QPS and verify it remains low (e.g., below a threshold). Ensure status updates are delivered in real-time without delays or excessive database queries.

- **Estimated effort:** 2 developer-days.

### 13. ChromaDB and Embedding model singletons not thread-safe

- **What to fix:** `backend/app/services/chroma_client.py` and `embedding.py` where module-level globals `_client` and `_local_model` are used, causing race conditions in multi-threaded contexts (e.g., concurrent Celery tasks).

- **How to fix:** Make the singletons thread-safe. For ChromaDB client, use a threading lock during initialization or adopt a factory pattern. For the embedding model, use thread-local storage or a singleton with locking mechanisms. Alternatively, leverage FastAPI's dependency injection to manage instances per request or task.

- **Dependencies:** Independent, but should be tested under concurrent access conditions.

- **Acceptance criteria:** Run concurrent tasks that access ChromaDB and embedding model (e.g., multiple analysis tasks) and verify no errors, race conditions, or data corruption occur. Use stress testing or unit tests to validate thread safety.

- **Estimated effort:** 1 developer-day.

### 14. Embedding model name hardcoded

- **What to fix:** `backend/app/services/embedding.py` where the embedding model name `text-embedding-3-small` is hardcoded, preventing users from switching models without code changes.

- **How to fix:** Make the embedding model name configurable via environment variables or a configuration file. Update the code to read the model name from settings (e.g., using `os.getenv` or a config module), allowing runtime adjustments.

- **Dependencies:** Independent of other fixes.

- **Acceptance criteria:** Set different embedding model names via environment variables (e.g., `EMBEDDING_MODEL_NAME`) and verify that the service uses the configured model. Test with at least two different models to ensure flexibility.

- **Estimated effort:** 0.5 developer-days.

### 15. No database connection pool configuration

- **What to fix:** `backend/app/database.py` where async and sync SQLAlchemy engines are created without explicit connection pool parameters, relying on defaults that may not suit production loads.

- **How to fix:** Configure connection pool parameters such as `pool_size`, `max_overflow`, `pool_recycle`, and `pool_timeout` based on expected load and database limits. Use environment variables to allow tuning per deployment.

- **Dependencies:** Independent of other fixes, but should be coordinated with database index changes for optimal performance.

- **Acceptance criteria:** Monitor connection pool usage under load and verify that connections are properly managed. Check that no connection leaks occur and that the application handles connection exhaustion gracefully.

- **Estimated effort:** 0.5 developer-days.

## Sprint-Level Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Database migration failures during index addition | Medium | High | Test migrations on staging environment first; maintain rollback scripts. |
| Race conditions in thread-safe singletons | Medium | Medium | Implement thorough concurrency testing; use established patterns. |
| Rate limiting affecting legitimate users | Low | Medium | Configure generous limits; implement per-user rate limiting with authentication. |
| Redis pub/sub implementation complexity | Medium | Medium | Start with simple implementation; iterate based on performance metrics. |
| Connection pool misconfiguration | Low | High | Use proven defaults; monitor in staging before production deployment. |

## Rollback Strategy

1. **Database Changes:** Maintain Alembic migration rollback scripts for all schema changes. Test rollbacks in staging environment.

2. **Application Code:** Use feature flags for rate limiting and CORS configuration to allow quick disabling if issues arise.

3. **Redis Pub/Sub:** Keep the original polling mechanism as a fallback, switchable via configuration.

4. **Connection Pool:** Revert to SQLAlchemy defaults if custom configuration causes issues.

## Overall Sprint B Acceptance Criteria

1. All foreign key columns have database indexes; query performance improves measurably.
2. Cleanup task deletes all related records; no orphan data remains.
3. Frontend communicates with backend without CORS errors.
4. Rate limiting prevents excessive API usage; returns 429 for abuse.
5. SSE mechanism reduces database QPS by at least 50% compared to polling.
6. ChromaDB and embedding services are thread-safe under concurrent load.
7. Embedding model is configurable via environment variables.
8. Database connection pool is configured and monitored.

**Total Estimated Effort:** 8.5 developer-days (approximately 2 weeks with buffer for testing and documentation).


---

## Sprint C: 可靠性与质量

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


---

## Sprint D + 项目总览

# Sprint D Overview: Testing & Documentation

## Part 1: Sprint D - Testing & Documentation (1 Week)

### Vulnerability Addressed
**25. LOW - Insufficient test coverage** (`tests/` directory)
Only 1 integration test file and 2 fixture contracts. Missing unit tests, boundary tests, security tests.

### Comprehensive Test Strategy Design

#### 1. Unit Tests for Services and Engines
- **What to test**: All service modules (AuthService, UploadService, AnalysisService, ResultService) and detection engines (SolidityDetector, SlitherIntegration, MythrilIntegration). Test business logic, input validation, error handling, and utility functions.
- **How to test**: Write pytest tests with high coverage. Use unittest.mock to isolate external dependencies (ChromaDB, PostgreSQL, Redis). Test edge cases like invalid inputs, empty data, and boundary conditions. Use parameterized tests for data-driven scenarios.
- **Priority**: P0
- **Estimated effort**: 3 developer-days

#### 2. Integration Tests for API Endpoints
- **What to test**: All FastAPI endpoints (/api/v1/auth/*, /api/v1/projects/*, /api/v1/analyses/*, /api/v1/results/*). Test request validation, authentication/authorization, database interactions, Celery task triggering, and SSE streaming.
- **How to test**: Use FastAPI TestClient with httpx for async testing. Set up test PostgreSQL/Redis databases. Test complete workflows: upload file 鈫?trigger analysis 鈫?get results. Verify HTTP status codes, response schemas, and error messages.
- **Priority**: P0
- **Estimated effort**: 4 developer-days

#### 3. Security Tests
- **What to test**: Path traversal in file uploads, prompt injection in LLM calls, authentication bypass (JWT tampering, expired tokens), authorization flaws (horizontal/vertical privilege escalation), rate limiting bypass, CSRF protection.
- **How to test**: Develop targeted security test cases. Use tools like pytest-security for common vulnerabilities. Test with malicious payloads (path traversal sequences, injection strings). Verify security headers and CORS policies.
- **Priority**: P0
- **Estimated effort**: 2 developer-days

#### 4. Performance Tests
- **What to test**: Rate limiting under high load, SSE connection stability with 100+ concurrent clients, large file upload handling (100MB+), database query performance with large datasets, Celery worker scaling.
- **How to test**: Use locust for load testing. Simulate concurrent users uploading files and triggering analyses. Monitor response times, error rates, and resource utilization. Test SSE with sustained connections.
- **Priority**: P1
- **Estimated effort**: 2 developer-days

#### 5. Edge Case Tests for File Upload
- **What to test**: Malicious archives (zip bombs, nested archives), empty files, files exceeding size limits, invalid file types, corrupted files, concurrent upload conflicts, temporary file cleanup.
- **How to test**: Create test fixtures for each edge case. Test upload validation, error handling, and cleanup mechanisms. Verify file system isolation and resource limits.
- **Priority**: P1
- **Estimated effort**: 1 developer-day

### Test Fixtures and Mock Strategies

**Shared Fixtures:**
- Database fixtures: Temporary PostgreSQL test database with schema migration
- Redis fixtures: Isolated Redis instance per test session
- File fixtures: Sample Solidity contracts (valid, vulnerable, malicious)
- Auth fixtures: Pre-authenticated test users with various roles
- Celery fixtures: In-memory Celery broker for task testing

**Mock Strategies:**
- ChromaDB: Mock vector search operations
- External APIs (Slither, Mythril): Mock analysis results
- File system: Use tmp_path for file operations
- Time-dependent tests: Mock datetime for rate limiting tests

### CI/CD Pipeline Integration

**Pipeline Stages:**
1. **Lint & Type Check**: flake8, mypy, pylint
2. **Unit Tests**: pytest --cov=app --cov-report=xml
3. **Integration Tests**: Separate test database, Redis container
4. **Security Scan**: bandit, semgrep, safety check
5. **Performance Tests**: Run on schedule (nightly/weekly)
6. **Coverage Report**: Enforce 80% minimum coverage for critical modules

**Quality Gates:**
- All tests must pass before merge
- Coverage threshold must be met
- No new security vulnerabilities
- Performance benchmarks within thresholds

### Documentation Requirements

**API Documentation:**
- Auto-generated OpenAPI/Swagger docs with examples
- Authentication flow documentation
- Error code reference
- Rate limiting documentation

**Architecture Documentation:**
- System component diagram (FastAPI + Celery + PostgreSQL + Redis + ChromaDB)
- Data flow diagrams for analysis pipeline
- Deployment architecture (Docker Compose)
- Monitoring and observability setup

**Runbooks:**
- Deployment runbook (zero-downtime deployment)
- Database migration runbook
- Incident response runbook
- Backup and recovery procedures

## Part 2: Dependency Graph

```
Sprint A (CRITICAL fixes) 鈫?Sprint B (HIGH fixes) 鈫?Sprint C (MEDIUM fixes) 鈫?Sprint D (Testing)

Dependencies within Sprints:

Sprint A:
#3 Route fix 鈫?#2 SSE auth (routes must exist before SSE)
#5 Input validation 鈫?#16 Error handling
#11 Upload limits 鈫?#7 Rate limiting

Sprint B:
#6 DB indexes 鈫?#12 Query optimization
#9 CORS 鈫?Frontend integration
#10 FP scoping 鈫?Requires understanding existing flow
#14 File cleanup 鈫?#15 Temp storage limits

Sprint C:
#19 State machine 鈫?#20 Task retry 鈫?#21 Celery config
#22 Log aggregation 鈫?#23 Structured logging 鈫?#24 Audit trail

Sprint D:
#25 Test coverage (requires all previous fixes completed)

Critical Path:
#3 鈫?#2 鈫?#19 鈫?#20 鈫?#21 鈫?#25
```

## Part 3: Risk Assessment

### Sprint A Risks
- **Risk**: Breaking existing API contracts during route restructuring
  - **Mitigation**: Maintain backward compatibility, version APIs, use feature flags
  - **Rollback**: Keep old route handlers, switch traffic back if issues
  - **Zero-downtime**: Blue-green deployment, gradual rollout

### Sprint B Risks
- **Risk**: Database index changes causing lock contention
  - **Mitigation**: Use online index creation, schedule during low traffic
  - **Rollback**: Drop indexes if performance degrades
  - **Zero-downtime**: Implement indexes concurrently

### Sprint C Risks
- **Risk**: State machine changes affecting running analyses
  - **Mitigation**: Implement dual-write, migrate gradually
  - **Rollback**: Revert to previous state handling
  - **Zero-downtime**: Maintain old and new state machines temporarily

### Sprint D Risks
- **Risk**: Test failures revealing undiscovered bugs
  - **Mitigation**: Gradual test enablement, monitor test stability
  - **Rollback**: Disable failing tests, prioritize fixes
  - **Zero-downtime**: Tests don't affect production

## Part 4: Timeline Estimate

**Assumptions:**
- 2 senior developers, 1 QA engineer
- 1-week sprints with buffer
- Start date: 2026-06-16

**Sprint Breakdown:**

| Sprint | Focus | Duration | Dev-Days | Key Deliverables |
|--------|-------|----------|----------|-------------------|
| A | CRITICAL fixes | 1 week | 10 | Secure routes, input validation, upload limits |
| B | HIGH fixes | 1 week | 10 | DB optimization, CORS, rate limiting |
| C | MEDIUM fixes | 1 week | 10 | State machine, logging, Celery config |
| D | Testing | 1 week | 8 | Comprehensive test suite, documentation |
| **Total** | | **4 weeks** | **38** | **Full remediation** |

**Critical Path:**
Route fix (#3) 鈫?SSE auth (#2) 鈫?State machine (#19) 鈫?Task retry (#20) 鈫?Test coverage (#25)
Estimated: 3.5 weeks

**Parallel Opportunities:**
- Sprint A: Input validation + Upload limits (same developer)
- Sprint B: DB indexes + CORS (different developers)
- Sprint C: Logging + Celery config (different developers)

**Calendar Timeline:**
```
Week 1 (Jun 16-20): Sprint A - CRITICAL fixes
Week 2 (Jun 23-27): Sprint B - HIGH fixes
Week 3 (Jun 30-Jul 4): Sprint C - MEDIUM fixes
Week 4 (Jul 7-11): Sprint D - Testing & Documentation
Week 5 (Jul 14-18): Buffer / Deployment preparation
```

**Resource Allocation:**
- Developer 1: Routes, Auth, State machine
- Developer 2: Database, Services, Celery
- QA Engineer: Test strategy, Security testing, Documentation

**Success Metrics:**
- 0 CRITICAL/HIGH vulnerabilities remaining
- >80% test coverage on critical modules
- Performance benchmarks maintained
- Complete documentation set
- Zero-downtime deployment capability

