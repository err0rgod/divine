# Aliases

Aliases are ordered lists of qualified model IDs. They give applications stable, operator-owned
names without hiding which candidates may be selected.

```toml
[aliases]
default = ["openai/model-a"]
fast = ["groq/model-b", "cerebras/model-c"]
cheap = ["provider/model-d"]
coding = ["openai/model-a"]
reasoning = ["provider/model-e"]
long-context = ["provider/model-f"]
vision = ["provider/model-g"]
```

Use `provider/model` for controlled verification. Use a named alias when the operator should be
able to change the backing model without changing client code. The `auto` value invokes automatic
routing and is not an ordinary alias.

Coding-agent profiles must resolve to an explicit qualified model or a non-automatic alias:

```toml
[cli_profiles.work]
model = "coding"
```

`divine routes` prints aliases and fallback chains without credential values.
