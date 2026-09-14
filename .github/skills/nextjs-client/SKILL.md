---
name: nextjs-client
description: "Use when building, debugging, testing, or reviewing this client: Next.js 16.3.5 App Router, React 19.2, TypeScript, Tailwind CSS 4, ESLint 9, and responsive UI in the client app."
argument-hint: "Describe the page, component, interaction, or frontend issue."
---

# Next.js Client

Use this skill for work under `client/`.

## Project Baseline

- The client uses Next.js 16.3.5, React 19.2, TypeScript, Tailwind CSS 4, and ESLint 9.
- Use the App Router under `client/app/`; keep route, layout, loading, error, and metadata conventions aligned with the installed Next.js version.
- Before changing Next.js behavior, read the relevant version-specific guide under `client/node_modules/next/dist/docs/` when dependencies are installed.
- Keep server components as the default. Add `"use client"` only for state, effects, event handlers, browser APIs, or client-only libraries.

## Implementation Rules

1. Inspect existing layouts, globals, and nearby components before adding new patterns or dependencies.
2. Keep data fetching on the server when possible; define clear loading, error, empty, and pending states for user-facing flows.
3. Use typed props and typed API results. Do not use `any` to bypass a contract problem.
4. Keep secrets and server-only credentials out of client components and browser bundles.
5. Follow the existing Tailwind 4 setup and responsive behavior. Avoid broad global CSS changes when local styles are sufficient.
6. Preserve accessible semantics, keyboard interaction, focus states, labels, and useful error messages.
7. Use optimized image and font handling appropriate to Next.js rather than raw browser primitives when the framework provides an equivalent.
8. Do not add visual filler or marketing structure to a functional screen; prioritize the user's actual workflow.

## Verification

From `client/`, run the narrowest relevant check first:

```powershell
npm run lint
```

For production validation:

```powershell
npm run build
```

Check the affected route at desktop and mobile widths, and verify server/client boundaries when changing data fetching or interactivity.
