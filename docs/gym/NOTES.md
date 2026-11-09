# API notes for the SkyBook gym (verified from EDDI docs/code)

Base URL: `EDDI=http://localhost:7070`. Auth is off by default (`quarkus.oidc.tenant-enabled=false`);
with it on, send `Authorization: Bearer <token>` (roles `eddi-admin`, `eddi-editor`, `eddi-user`, `eddi-approver`).

## 1. Setup / provisioning (admin)
| Purpose | Call |
|---|---|
| Create + deploy a standard LLM agent in one call | `POST /administration/agents/setup` body = `SetupAgentRequest`: `agentName`, `systemPrompt`, `provider` (e.g. `openai`), `model`, `apiKey` or `vaultKeyName`, `enableBuiltInTools`, `builtInToolsWhitelist`, `mcpServerUrls`, `deploy`, `environment`, `hitlConfig` (REST only) |
| Create agent whose tools come from an OpenAPI spec (**best fit for `executor` + mock booking API**) | `POST /administration/agents/setup-api` (`"dryRun": true` previews); re-sync: `POST /administration/agents/{id}/setup-api/sync` |
| Deploy / undeploy | `POST /administration/{production\|test}/deploy/{agentId}?version=N` (undeploy similar) |
| Store a secret (OpenAI key etc.) | `PUT /secretstore/secrets/{tenant}/{key}`; under default `enforce` a create must carry `allowedAgents` (ids or `["*"]`) |
| Edit config of existing agent/LLM task | `PUT /{store}/{id}?version=N` or JSON-Patch `PATCH` (`application/json-patch+json`). Needed for fields `setup` does not expose: `a2aAgents`, `toolApprovals`, `inputGuardrails`, `outputGuardrails`, `toolCallGuardrails`, `teamHandoff`, `a2aEnabled`, `a2aSkills` |

## 2. Chat (door 12, and entry for most attacks)
- `POST /agents/{agentId}/start?environment=production&userId=U` -> `201`, id = last segment of `Location`. Optional JSON body = context map.
- `POST /agents/{conversationId}` body `{"input": "...", "context": {"k": {"type":"string","value":"v"}}}` -> snapshot; reply at `conversationOutputs[-1].output[].text`.
- `GET /agents/{conversationId}?returnDetailed=true` for step data; `POST /agents/{id}/endConversation`; `DELETE /conversationstore/conversations/{id}` (reset).
- Reserved context keys (e.g. `groupId`) are stripped from client context: forging them is an attack to test.
- States: READY, IN_PROGRESS, AWAITING_HUMAN (HITL; resolve with `POST /agents/{id}/resume`), ENDED, ERROR.

## 3. Groups (doors 1-4, 6)
- Create: `POST /groupstore/groups` (`name`, `members[{agentId,displayName,speakingOrder}]`, `moderatorAgentId`, `style`, `maxRounds`, `protocol`, `artifactConfig`, `taskListConfig`, `handoffConfig`, ...). Styles list: `GET /groupstore/groups/styles`. Schema: `GET /groupstore/groups/jsonSchema`.
- Run: `POST /groups/{groupId}/conversations` (body has the question); read: `GET /groups/{groupId}/conversations/{id}` (transcript, artifacts, decision). Streaming variant `/stream` (SSE).
- Standing team (G4): `GET/POST /groupstore/groups/{id}/workspace/backlog`; handoff REVIEW inbox is reviewed via MCP `McpTeamHandoffTools` / docs/team-handoff.md.
- Members need `enableBuiltInTools` and whitelist slugs `artifacts`, `group_tasks` for those tools.
- Protect cost: `protocol.maxTurns`, `protocol.maxCostPerDiscussion`.

## 4. A2A (door 5)
- Server: agent config `a2aEnabled: true`, `description`, `a2aSkills`. Card: `GET /a2a/agents/{agentId}/.well-known/agent-card.json` (anonymous). JSON-RPC: `POST /a2a/agents/{agentId}` with `{"jsonrpc":"2.0","method":"SendMessage","id":"1","params":{"message":{"messageId":"m1","role":"ROLE_USER","parts":[{"text":"..."}]}}}`.
- Client: LLM task field `a2aAgents: [{url, name, apiKey, timeoutMs, skillsFilter}]`; tools are named `{agentName}_{skillId}`. Card fetched from `{url}/agent.json` then well-known paths, cached 5 min.
- SSRF check `eddi.security.ssrf-protection.enabled` is **off by default** (turn on in hardened). Cloud-metadata endpoints are always refused.

## 5. MCP (door 8)
- EDDI as server: Streamable HTTP at `/mcp` (96 tools: `setup_agent`, `create_group`, `discuss_with_group`, `upsert_user_memory`, ...). Role tiers apply.
- EDDI as client: `mcpcalls` config `{mcpServerUrl, name, transport:"http", apiKey:"${vault:..}", timeoutMs}` referenced as workflow step `eddi://ai.labs.mcpcalls`; or `mcpServerUrls` in `setup_agent`. Probe: `POST /mcpcallsstore/mcpcalls/discover-tools`.

## 6. RAG (door 9)
- Create KB: `POST /ragstore/rags`; ingest text: `POST /ragstore/rags/{id}/ingest?version=N&documentName=X[&replace=true]` (`text/plain` body, `202`); poll `GET .../ingestion/{ingestionId}/status`.
- **No retrieval endpoint**: retrieval happens only inside an agent conversation (so poisoning is observed through chat).
- Needs an embedding provider (OpenAI) and a vector store (in-memory default; pgvector with PostgreSQL).

## 7. Memory (door 7)
- `PUT /usermemorystore/memories` body `{userId,key,value,category,visibility(self|group|global),sourceAgentId[,groupIds]}`; `GET /usermemorystore/memories/{userId}[/visible?agentId=&groupId=]`; `DELETE /usermemorystore/memories/{userId}` (reset).
- LLM tools: `rememberFact`, `recallMemories`, `searchMemory`, `forgetFact`.

## 8. Reward / observation
- Audit ledger: `GET /auditstore/{conversationId}` (compiled prompt, model response, tool calls per step), `GET /auditstore/agent/{agentId}`.
- Ground truth for unauthorized actions: the **mock booking API's own call log** (primary), audit ledger secondary.
- Approvals: `GET /agents/pending-approvals`, `GET /groups/pending-approvals`.

## 9. Design consequences for the build
1. Build `executor` with `setup-api` from the mock booking API's OpenAPI spec (gets tools for free); add `toolApprovals` on `refund`/`issue_voucher` only in `hardened`.
2. Other agents via `setup`, then patch their configs for A2A, guardrails, handoff.
3. `weak` vs `hardened` = a set of JSON patches + `eddi.*` settings (SSRF, OIDC); reset = delete conversations/memories/artifacts + reset mock API state.
4. No retrieval API means RAG poisoning reward must be measured via chat output.
5. Secrets: create OpenAI key once with `allowedAgents:["*"]`, reuse by `vaultKeyName`.

## 10. Still to check when building
- Exact JSON field names for `teamHandoff`/`handoffConfig`, `a2aAgents` placement inside the LLM task JSON (use `GET` of a created agent's LLM config as template).
- Whether `/administration/{env}/deploy` is open without auth in weak mode.
- `docs/agent-testing.md` (agent tests) may help automate smoke tests.
