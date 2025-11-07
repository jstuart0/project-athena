# Thoughts Directory

This directory contains research, technical specifications, architectural decisions, and other documentation that captures the "why" behind code changes in Project Athena.

## Purpose

The `thoughts/` directory serves as a historical record of:
- Technical investigations and research findings
- Implementation plans and specifications
- Architectural decisions (ADRs)
- Pull request summaries and analysis
- Design explorations

Unlike `docs/` which contains user-facing documentation, `thoughts/` documents the development process and decision-making for the engineering team.

## Directory Structure

```
thoughts/
├── shared/              # Team-shared, version-controlled content
│   ├── research/        # Technical investigations and findings
│   ├── plans/           # Implementation plans and specifications
│   ├── decisions/       # Architecture Decision Records (ADRs)
│   └── prs/             # Pull request summaries and analysis
├── local/               # Personal notes (gitignored)
└── searchable/          # Hard links for fast searching (optional, gitignored)
```

### `shared/` - Team Content

**Version-controlled content that's shared with the team.**

#### `shared/research/`
Technical investigations that document how things work, what was discovered, and findings from codebase exploration.

**Naming convention**: `RESEARCH_<topic>.md` or `YYYY-MM-DD-topic-description.md`
- Example: `RESEARCH_HA_LLM_FACADE.md`
- Example: `2025-11-07-jetson-orin-performance.md`

**Suggested frontmatter**:
```yaml
---
date: 2025-11-07T13:34:05+0000
researcher: jaystuart
git_commit: abc123def
branch: feature/ha-integration
repository: project-athena
topic: "Brief description of research topic"
tags: [research, home-assistant, llm, integration]
components: [ha-llm-facade, athena-lite]
status: complete
last_updated: 2025-11-07
last_updated_by: jaystuart
---
```

#### `shared/plans/`
Implementation plans, technical specifications, and design documents.

**Naming convention**: `YYYY-MM-DD-feature-name.md`
- Example: `2025-01-06-ha-llm-facade-production.md`

#### `shared/decisions/`
Architecture Decision Records (ADRs) documenting significant architectural choices.

**Naming convention**: `YYYY-MM-DD-decision-title.md` or `ADR_<number>_<topic>.md`

**Template**:
```markdown
# Decision: [Title]

## Status
[Proposed | Accepted | Deprecated | Superseded]

## Context
What is the issue we're trying to solve?

## Decision
What did we decide to do?

## Consequences
What are the positive and negative outcomes?

## Alternatives Considered
What other options did we evaluate?
```

#### `shared/prs/`
Pull request summaries, code review findings, and PR-related analysis.

### `local/` - Personal Notes

**Gitignored directory for personal exploration and notes.**

Use this for:
- Scratch notes during debugging
- Personal TODO lists
- Experimental ideas not ready to share
- Quick observations

### `searchable/` - Search Optimization

**Optional directory containing hard links to all documents for fast grep/ripgrep searching.**

This directory is gitignored. If you want to use it:
```bash
# Create hard links for all markdown files
find thoughts/shared -name "*.md" -exec ln {} thoughts/searchable/ \;

# Search all thoughts
rg "search term" thoughts/searchable/
```

## Component Tags

Since Project Athena involves multiple systems and integrations, use **component tags** in frontmatter:

```yaml
components: [ha-llm-facade, athena-lite, jetson-deployment]
```

**Available component tags**:
- `ha-llm-facade` - Home Assistant LLM integration facade
- `athena-lite` - Lightweight runtime system
- `jetson-deployment` - NVIDIA Jetson deployment configurations
- `kubernetes` - K8s manifests and deployment
- `model-server` - LLM model serving infrastructure
- `config-management` - Configuration systems
- `monitoring` - Observability and monitoring

## Searching Thoughts

**Find research by topic**:
```bash
grep -r "tags:.*jetson" thoughts/shared/research/
```

**Find research by component**:
```bash
grep -r "components:.*ha-llm-facade" thoughts/shared/
```

**Find all research by a specific person**:
```bash
grep -r "researcher: jaystuart" thoughts/shared/research/
```

**Find research from a specific date range**:
```bash
ls thoughts/shared/research/2025-11-*
```

## Best Practices

1. **Research documents are snapshots** - Include git commit hash and branch in frontmatter
2. **Link to code** - Use file paths with line numbers: `file.py:123`
3. **Update existing documents** - Add follow-up sections rather than creating duplicates
4. **Cross-reference** - Link related research documents
5. **Use tags liberally** - Makes searching easier
6. **Date in filename** - Keeps chronological order, easy to see age
7. **Component tags** - Indicate which parts of Project Athena are relevant

## Workflow Integration

### When Creating Research (via /research_codebase)

1. Research is conducted by spawning parallel agents
2. Document is written to `thoughts/shared/research/` with frontmatter
3. Document includes file references and code locations
4. Tags indicate relevant components

### When Writing Plans (via /create_plan)

1. Implementation plan created in `thoughts/shared/plans/`
2. Plan includes acceptance criteria and verification steps
3. Plan references related research documents
4. Update plan as implementation progresses

### When Making Architectural Decisions

1. Create ADR in `thoughts/shared/decisions/`
2. Document alternatives considered
3. Capture trade-offs and consequences
4. Reference from code comments if needed

## Example Research Documents

Current research:
- `shared/research/RESEARCH_HA_LLM_FACADE.md` - Home Assistant LLM Integration Facade
- `shared/research/RESEARCH_JETSON_ITERATIONS.md` - Jetson deployment iterations

These documents demonstrate:
- Technical investigation methodology
- Code references with file paths
- Clear explanation of findings
- Component tagging

## Tools

**No special tools required** - thoughts/ is just markdown files tracked by git.

If you want advanced features:
- ripgrep (`rg`) - Fast searching
- fzf - Fuzzy finding thoughts documents

## Related Documentation

- **CLAUDE.md** - Claude Code instructions for working with this codebase
- **docs/** - User-facing documentation
- **README.md** - Project overview
