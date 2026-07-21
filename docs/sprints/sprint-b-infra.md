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
