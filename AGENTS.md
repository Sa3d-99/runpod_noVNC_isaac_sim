# Project knowledge

Read [docs/knowledge-base/README.md](docs/knowledge-base/README.md) before substantial investigation or implementation. It links the authored architecture, Gazebo decisions, and validation evidence.

- Graphify graph: `graphify-out/graph.json`; report: `graphify-out/GRAPH_REPORT.md`.
- Local Obsidian vault: `graphify-out/obsidian/`; interactive graph: `graphify-out/graph.html`.
- Use `/home/sa3d/.codex/skills/graphify/SKILL.md` and `/home/sa3d/.local/bin/graphify` for graph queries and incremental updates. Verify graph findings against current sources.
- Generated graphs and extraction caches are local and ignored by Git. Rebuild if absent; exclude dependencies, build output, generated vault exports, and secrets using `.graphifyignore`.
- Keep durable notes in `docs/knowledge-base/`. Preserve authored notes when regenerating the vault, and incorporate these notes into it. The standing project workflow authorizes Obsidian export.

The default simulator is Isaac Sim. Gazebo is an optional mode restricted to Ubuntu 22.04 / ROS Humble and Ubuntu 24.04 / ROS Jazzy. Preserve the shared desktop workflow and keep validation claims aligned with the recorded evidence.
