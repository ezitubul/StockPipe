# Schema validation — shared rule (applies to every file in this directory)

For each source, hash the field-name set (not values) of each response type. Compare against last-known-good hash stored in cache. Mismatch → fetch-agent HALTs, does not parse the response body, escalates to orchestrator per its protocol.

Per-source field lists below are informational only — the hash covers the field-name set, not this document.
