# Provider compatibility

The initial catalogue contains templates for OpenAI, Anthropic, Gemini, DeepSeek, Groq, Cerebras,
NVIDIA, Mistral, xAI, Together, Fireworks, SambaNova, Cohere, Hugging Face, Cloudflare Workers AI,
Perplexity, Azure OpenAI, Ollama, LM Studio, OpenRouter, and generic OpenAI/Anthropic providers.
Bedrock and Vertex are extension entries. Gateway entries without a confirmed compatible endpoint
remain disabled.

| Capability evidence | Current status |
|---|---|
| Template exists | Yes for the catalogue above |
| Family adapter mock-tested | OpenAI-compatible, Anthropic, Gemini |
| Client protocol mock-tested | Chat, Responses, Messages, SSE, tools, failures |
| Official SDK smoke-tested | OpenAI and Anthropic against local ASGI app |
| Provider live-tested | None; Groq and DeepSeek credentials returned 401 during discovery |
| Real coding-agent end-to-end | None recorded yet |

No provider is marked `verified-live` solely because its URL or authentication format was checked
against documentation. The root `PROVIDER_COMPATIBILITY.md` is the build-time evidence matrix and
`BUILD_REPORT.md` records executed gates.

The build attempted one bounded request each for Groq and DeepSeek. Both stopped at model
discovery with an authentication failure, no completion was billed, and neither credential was
retried. Other discovered credentials were intentionally not probed in bulk.

## Known limitations

- Vendor-specific extensions are not automatically portable.
- Gemini-native streaming/tool behavior needs provider-specific live validation.
- Azure deployments require editable resource and deployment-specific configuration.
- Cloudflare requires an account-specific base URL.
- Bedrock and Vertex require dedicated authentication/signing work.
- Model capability and pricing metadata can become stale; keep both editable and date-stamped.
