---
description: Scaffold a new REST route following project conventions (envelope, DI, tests)
argument-hint: <method> <path> [— description]
---

The user wants to add a new route. Arguments: $ARGUMENTS

Use the `route-builder` subagent to do the scaffolding — it knows the project's envelope, dependency-injection, and test conventions.

Before dispatching, do these two things in this conversation:

1. Parse the arguments. Identify the HTTP method, the path, and any free-form description. If the path or method is missing or ambiguous, ask the user to clarify before continuing.
2. Confirm the request and response shape with the user (field names + types). The subagent will need this concretely; don't make it guess.

Then dispatch the `route-builder` subagent with: method, path, request fields, response fields, and any failure modes the user wants tested.
