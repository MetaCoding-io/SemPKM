# M035 Research: AI Copilot & LLM Test Harness

Research completed 2026-03-22. Key findings:

- LLM infrastructure exists: LLMConfigService (Fernet-encrypted keys), SSE proxy in settings.py, M028 AI router (6 endpoints, 1119 lines) — NOT wired into main.py
- AI COPILOT tab placeholder in workspace.html bottom panel — "coming in v2.1"
- Schema context available via ShapesService.get_node_shapes() + SPARQL vocabulary endpoint
- SPARQL execution pipeline reusable: inject_prefixes() → scope_to_current_graph() → client.query()
- Persona system pattern in persona/ module — reusable for AI personas (different table, same lifecycle)
- 1981 lines of existing M028 AI tests across 4 files
- Mock LLM server exists (348 lines) but not in docker-compose.test.yml
- Highest risk: SPARQL generation quality — needs multi-layer validation

See M035-RESEARCH.md for full analysis including slice boundary recommendations, candidate requirements (AI-01 through AI-17), and technology assessment.