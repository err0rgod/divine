# Provider Compatibility

No provider is marked live-tested in this build. Adapter behavior is mocked; provider templates
are disabled until credentials and models are explicitly configured. One bounded request each was
attempted for Groq and DeepSeek, but both stored credentials were rejected with HTTP 401 before a
completion; neither credential was retried.

| Provider family | Template | Mock-tested | Live-tested | Streaming | Tools | Notes |
|---|---:|---:|---:|---:|---:|---|
| OpenAI-compatible | Yes | Yes | No | Yes | Yes | Shared by direct providers and gateways |
| Anthropic Messages | Yes | Yes | No | Converter tested | Yes | Native Messages translation |
| Gemini | Yes | Payload tested | No | Implemented | Implemented | Live behavior unverified |
| AWS Bedrock | Extension | No | No | No | No | Requires SigV4 extension |
| Google Vertex AI | Extension | No | No | No | No | Requires ADC extension |

## Live-test matrix (2026-07-19)

| Provider | Model requested | Discovery | Completion | Result |
|---|---|---:|---:|---|
| Groq | `llama-3.1-8b-instant` | 401 | Not attempted | Credential unavailable |
| DeepSeek | `deepseek-v4-flash` | 401 | Not attempted | Credential unavailable |
| All others | — | Not run | Not run | Not probed to avoid broad credential charges |

Templates exist for OpenAI, Anthropic, Gemini, DeepSeek, Groq, Cerebras, NVIDIA, Mistral, xAI,
Together, Fireworks, SambaNova, Cohere, Hugging Face, Cloudflare, Perplexity, Azure OpenAI,
Ollama, LM Studio, OpenRouter, AgentRouter, Forge, BluesMinds, and generic custom endpoints.

AgentRouter's current official API is capability-oriented, so its template stays disabled until
a dedicated adapter exists. Forge's public site did not expose an official API base path during
research, so that template also remains disabled instead of inventing an endpoint. AnyScale is
omitted because no current active official public API was confirmed.

Official references used for URL and compatibility checks include the provider documentation for
[OpenAI](https://developers.openai.com/api/reference/resources/responses/methods/create),
[Anthropic](https://docs.anthropic.com/en/api/messages),
[Gemini](https://ai.google.dev/api/generate-content),
[DeepSeek](https://api-docs.deepseek.com/),
[Groq](https://console.groq.com/docs/openai),
[Cerebras](https://inference-docs.cerebras.ai/resources/openai),
[Mistral](https://docs.mistral.ai/api/endpoint/models),
[Together](https://docs.together.ai/docs/inference/openai-compatibility),
[Fireworks](https://docs.fireworks.ai/tools-sdks/openai-compatibility),
[Cohere](https://docs.cohere.com/docs/compatibility-api),
[Hugging Face](https://huggingface.co/docs/inference-providers/en/index), and
[Cloudflare](https://developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility/).
