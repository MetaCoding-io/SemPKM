# .meta — Repository Mapping & Visualization Tools

Tools for generating architecture diagrams, code maps, and AI-friendly repository representations at multiple levels of detail.

## Quick Start

```bash
# Start CodeCharta Web Studio (interactive 3D visualization)
docker compose -f .meta/docker-compose.yml up codecharta-web
# Open http://localhost:9100

# Generate code metrics for CodeCharta
docker compose -f .meta/docker-compose.yml run --rm codecharta-analyze

# Generate full AI-friendly repo map (XML with all details)
docker compose -f .meta/docker-compose.yml run --rm repomix-full

# Generate compressed repo map (~70% fewer tokens)
docker compose -f .meta/docker-compose.yml run --rm repomix-compressed
```

## Tools

### 1. Repomix (AI Repo Maps)

Packs the entire repository into a single AI-optimized file. Two modes:

| Mode | Command | Output | Use Case |
|------|---------|--------|----------|
| **Full** | `run --rm repomix-full` | `output/repomix-output.xml` | Complete repo context for AI |
| **Compressed** | `run --rm repomix-compressed` | `output/repomix-compressed.xml` | Reduced tokens (~70% less) via Tree-sitter |

Both modes include:
- Directory structure tree
- File summaries with token counts
- Git history (full mode only)
- Security scanning (detects leaked secrets)

**Configuration:** Edit `repomix.config.json` or `repomix-compressed.config.json`.

**Standalone usage** (without docker-compose):
```bash
.meta/scripts/repomix-full.sh
.meta/scripts/repomix-compressed.sh
```

### 2. CodeCharta (3D Code City Visualization)

Transforms code metrics into interactive 3D city maps. Buildings = files, height = complexity, area = lines of code, color = change frequency.

**Step 1: Analyze** — generates `.cc.json.gz` metric files:
```bash
docker compose -f .meta/docker-compose.yml run --rm codecharta-analyze
```

This runs three parsers and merges results:
- **Git Log Parser** — change frequency, authors, age of files
- **Tokei** — lines of code, language breakdown, complexity
- **Raw Text Parser** — indentation-based complexity metrics

**Step 2: Visualize** — open the Web Studio:
```bash
docker compose -f .meta/docker-compose.yml up codecharta-web
# Open http://localhost:9100
# Upload .meta/output/codecharta/sempkm-merged.cc.json.gz
```

**Standalone analysis** (without docker-compose):
```bash
.meta/scripts/codecharta-analyze.sh
```

### 3. Swark (LLM-Powered Architecture Diagrams) — VS Code Extension

Generates architecture diagrams automatically using LLMs. Install directly in VS Code:

1. Open VS Code Extensions panel (`Ctrl+Shift+X`)
2. Search for **"Swark"**
3. Install it
4. Open Command Palette (`Ctrl+Shift+P`) → **"Swark: Create Architecture Diagram"**

Works with GitHub Copilot — no API key needed. Generates Mermaid diagrams showing module dependencies and data flow.

- GitHub: https://github.com/swark-io/swark
- Marketplace: Search "Swark" in VS Code Extensions

## Output Files

All generated output goes to `.meta/output/` (git-ignored):

```
.meta/output/
├── repomix-output.xml              # Full AI repo map
├── repomix-compressed.xml          # Compressed AI repo map
└── codecharta/
    ├── git.log                     # Raw git log
    ├── gitlog-analysis.cc.json.gz  # Git metrics
    ├── tokei-analysis.cc.json.gz   # Source code metrics
    ├── rawtext-analysis.cc.json.gz # Text complexity metrics
    └── sempkm-merged.cc.json.gz   # Merged (upload this to Web Studio)
```

## Architecture

```
.meta/
├── docker-compose.yml              # All services
├── repomix.config.json             # Full mode config
├── repomix-compressed.config.json  # Compressed mode config
├── scripts/
│   ├── repomix-full.sh             # Standalone full map script
│   ├── repomix-compressed.sh       # Standalone compressed map script
│   ├── codecharta-analyze.sh       # Standalone analysis script
│   └── codecharta-docker-entrypoint.sh  # Container entrypoint
├── output/                         # Generated files (git-ignored)
└── README.md                       # This file
```

## Port Map

| Service | Port | URL |
|---------|------|-----|
| CodeCharta Web Studio | 9100 | http://localhost:9100 |
| *(Main app frontend)* | 3000 | http://localhost:3000 |
| *(Main app API)* | 8001 | http://localhost:8001 |
