# UI State Sequences

## Accounts and rates

`idle -> loading -> success(seeded rows)`; `idle -> loading -> success(empty)`; `idle -> loading -> error(retry)`; at narrow viewport, the same states use stacked cards/table overflow containment.

## Statement

`unselected -> selected -> loading -> success(lines)`; `selected -> loading -> empty`; `selected -> loading -> error(retry)`; statement rows show deterministic running balance and reversal labels.

## Posting

`closed -> open -> editing -> submitting(disabled controls) -> success(refresh accounts/statement)`; invalid input remains `editing` with inline Error_Envelope message; network failure returns to `editing` with retry affordance; responsive layout stacks line editors.

## Reversal

`posted row -> confirmation dialog -> submitting -> success(refresh)`; duplicate/conflict -> error state with original row preserved; cancellation returns to posted row without mutation.

## Global behavior

Every request has visible loading feedback, every empty collection has explanatory copy, every failed request has a retry path, successful mutations provide confirmation, and all controls support keyboard focus. No inline styles are permitted.
