# Code Structure and Conventions

## Backend
- Flat import surface under `backend/`: `models`, `api`, and `engine` are top-level packages because `backend/Dockerfile` sets `PYTHONPATH=/app`.
- `api/routes.py` owns Pydantic request/response schemas, dependency injection, route orchestration, and HTTP error mapping.
- `engine/*_service.py` uses static methods rather than injected service instances or repositories.
- `models.py` contains all ORM models and enums in one module.
- Tests are separated into `tests/unit`, `tests/integration`, and `tests/property`; fixtures live in `tests/fixtures/factories.py`.

## Frontend
- `src/App.tsx` owns only two-tab view state.
- Feature components are in `src/components/`; primitive UI components are in `src/components/ui/`.
- `src/lib/api.ts` is a thin fetch client with hand-written interfaces.
- Tailwind utility classes and CSS variables in `src/index.css` are the design mechanism.
- `@/*` aliases to `src/*` via Vite and TypeScript.

## Conventions to retain selectively
- Decimal strings across the API for monetary values.
- Direct array responses for account/rate list endpoints and direct objects for balance/statement/entry responses.
- Read-only balance derivation from posted journal lines.
- Separate service boundaries for posting, balance, accrual, and reversal.

## Conventions to replace in a clean rebuild
- Flat backend imports and module-global DB engine/session factory.
- Route-local response construction duplicated for posting and reversal.
- Component-level data fetching without a shared error/empty/loading policy.
- Generic `str` route parameter for reversal IDs instead of UUID validation.
