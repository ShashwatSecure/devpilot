---
name: fullstack-integration
description: "Use when connecting the Next.js client to the Spring Boot backend, designing API contracts, handling CORS, OAuth2 sessions, errors, loading states, environment variables, or end-to-end behavior across client and backend."
argument-hint: "Describe the client-backend flow or contract that needs to change."
---

# Full-Stack Integration

Use this skill when a change crosses `client/` and `backend/`.

## Procedure

1. Identify the owning backend endpoint and the client call site before editing either side.
2. Write down the request, response, status codes, authentication assumptions, and failure cases before changing the contract.
3. Keep the backend contract explicit with DTOs and validation. Mirror it in typed client request and response definitions.
4. Decide where the call runs: server-side in Next.js for protected or secret-bearing work, or client-side only when browser interactivity requires it.
5. Configure URLs and credentials through environment variables. Never commit tokens, API keys, or environment-specific secrets.
6. Handle CORS, cookies, CSRF, OAuth2 redirects, and authorization as one flow; do not solve browser failures by weakening security globally.
7. Make loading, empty, unauthorized, forbidden, validation, server-error, and network-failure states visible and actionable in the client.
8. Keep compatibility in mind when changing an endpoint. Prefer additive changes or a deliberate migration over silently changing response shapes.

## Verification

- Run the focused backend test and `npm run lint` for the client.
- Exercise the endpoint with valid, invalid, unauthenticated, and unauthorized requests.
- Verify cookies or bearer tokens, CORS headers, redirects, and error payloads in a browser or HTTP client.
- Run `npm run build` when changing server/client boundaries, environment usage, routing, or generated types.
