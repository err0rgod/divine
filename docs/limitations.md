# Limitations

Divine Router deliberately reports a compatibility subset.

- Responses hosted tools and stateful conversation storage are rejected.
- Provider-specific extensions may not have a canonical representation.
- Exact provider token counting is not available for every adapter.
- Mid-stream retry/fallback is prohibited after visible output.
- Capability and pricing metadata require operator maintenance; pricing is date-stamped, not a
  guarantee.
- Bedrock and Vertex expose extension architecture but are not complete initial adapters.
- Provider templates have mocked/documentation evidence unless explicitly marked live.
- The TUI is an operations/configuration interface, not a chat client.
- Local rate limiting is process-local and is not a distributed quota system.
- SQLite is intended for local metadata, not multi-node coordination.
- The Aider wrapper is unavailable without a verified compatible installed version.

Review the [provider matrix](provider-compatibility.md) and build report before production use.
