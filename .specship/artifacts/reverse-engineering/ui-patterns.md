# UI Patterns

## Current screens
- Global header “nbus Ledger” in `frontend/src/App.tsx`.
- Two local-state tabs: Accounts and Rate Schedule.
- Accounts card/table with code, name, type badge, normal balance; clicking a row expands an inline statement.
- Statement card/table with date, short entry ID, debit, credit, running balance, and reversal badge; separate balance query in header.
- Rate schedule card/table showing tier and APY percentage.

## Current design system
Tailwind CSS with shadcn-like CSS variables in `frontend/src/index.css`; Card/Table/Badge/Button primitives under `frontend/src/components/ui/`. Light slate palette, 0.5rem radius, no dark-mode tokens beyond Tailwind configuration.

## Current strengths
- Shared primitives are used rather than inline styles.
- Monetary values remain strings until display conversion.
- Main list and statement include loading/error/statement-empty branches.

## Current weaknesses to address in rebuild
- No true account seed in migration, so the default UI has an empty accounts table.
- Rate empty state is blank table rather than an explanatory state.
- `<tr onClick>` is not a keyboard semantic control.
- Account list has no explicit empty state, refresh, retry, or active/inactive presentation.
- No posting/reversal UI despite write and reversal API concepts.
- Component tests shallowly invoke function components and do not assert accessible DOM behavior.
- `Number()` conversion for display is acceptable for percentage rendering but should not be used for money arithmetic.
