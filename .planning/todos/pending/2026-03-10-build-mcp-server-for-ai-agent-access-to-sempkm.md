---
created: 2026-03-10T05:43:47.184Z
title: Build MCP server for AI agent access to SemPKM
area: api
files: []
---

## Problem

Users want to give their AI models (Claude, GPT, etc.) direct access to their SemPKM knowledge base via the Model Context Protocol (MCP). Currently there is no machine-oriented interface — the only access paths are the browser UI and raw SPARQL. An MCP server would let AI agents browse objects, query the knowledge graph, read/write properties, and run SPARQL — all through a standardized tool-use protocol.

## Solution

Build an MCP server as a future milestone. Key capabilities to expose:

- **Browse/search objects** — list types, search by label, get object details
- **Read properties** — fetch an object's properties and relations
- **Write/update** — create objects, add/edit properties (with SHACL validation)
- **SPARQL query** — run read-only SPARQL against the triplestore
- **Graph traversal** — follow relations, get neighbors, explore paths
- **Lint/inference** — trigger validation, read lint results

Implementation options:
1. Standalone MCP server process that calls the existing FastAPI backend
2. MCP transport layer directly in the FastAPI app (e.g., SSE-based MCP)
3. Separate lightweight service sharing the triplestore connection

Should align with the MCP specification (https://modelcontextprotocol.io/) and support both stdio and SSE transports for flexibility.
