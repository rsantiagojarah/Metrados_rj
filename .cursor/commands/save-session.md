# /save-session

Force a local deterministic session checkpoint.

Invoke memory:save with the current local session identifiers: any text following the slash command
Run `npx @ericrisco/rsc memory save --session <id>`. Persist only allowed git and SDD ledger metadata; never include conversation or file content.
