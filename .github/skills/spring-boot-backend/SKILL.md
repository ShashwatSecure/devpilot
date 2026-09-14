---
name: spring-boot-backend
description: "Use when building, debugging, testing, or reviewing this Java backend: Spring Boot 4.1.x, Java 21, Spring MVC, Spring Data JPA, PostgreSQL, OAuth2 client security, Spring AI 2.x, Maven, and Lombok."
argument-hint: "Describe the backend feature, failing test, or API behavior."
---

# Spring Boot Backend

Use this skill for work under `backend/`.

## Project Baseline

- Java 21 and Spring Boot 4.1.1 are the project baseline.
- Use Maven through `backend/mvnw.cmd` on Windows and `backend/mvnw` on Unix-like systems.
- Existing dependencies include Spring MVC, Spring Data JPA, PostgreSQL, OAuth2 client security, Spring AI OpenAI, Lombok, and Spring Boot test starters.
- Keep configuration in `backend/src/main/resources/application.yaml`; never hard-code credentials or API keys.

## Implementation Rules

1. Inspect nearby packages and existing configuration before introducing a new layer or dependency.
2. Keep controllers focused on HTTP concerns, services focused on application behavior, and repositories focused on persistence.
3. Define explicit request and response DTOs at API boundaries; do not expose JPA entities directly unless the existing API intentionally does so.
4. Use constructor injection and immutable data where practical. Preserve the repository's Lombok conventions when they exist.
5. Validate input at the boundary and return consistent HTTP error responses. Do not leak provider, database, or secret details.
6. Treat OAuth2 and Spring AI calls as external boundaries: isolate them behind services, handle timeouts and failures, and keep secrets in environment-backed configuration.
7. For persistence changes, consider transaction boundaries, indexes, nullability, migrations, and PostgreSQL behavior before coding.

## Verification

From `backend/`, run the narrowest relevant check first:

```powershell
.\mvnw.cmd test
```

If only compilation is needed:

```powershell
.\mvnw.cmd -DskipTests compile
```

Add or update focused tests for controller, service, repository, security, and AI integration behavior as appropriate. Prefer Spring test slices for isolated behavior and full context tests only when wiring or configuration is the subject.
