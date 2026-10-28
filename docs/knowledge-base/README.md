# Project knowledge

The project provides a browser desktop for NVIDIA Isaac Sim on RunPod. Its application source was restored from commit `cfdca8f`; the user subsequently authorized targeted lifecycle, startup, and installer hardening while keeping the project Isaac-only.

- [Architecture and preserved behavior](architecture.md)
- [Gazebo separation and provenance](migration.md)
- [Validation evidence and unresolved runtime checks](validation.md)
- [SSH and browser-terminal investigation](ssh-terminal-investigation.md)
- [User setup and commands](../../README.md)
- [Original streaming investigation](../../POSTMORTEM.md)

Durable authored notes live here. The local Graphify graph is `graphify-out/graph.json`, its audit report is `graphify-out/GRAPH_REPORT.md`, and its interactive view is `graphify-out/graph.html`. Open `graphify-out/obsidian/` as the project's Obsidian vault; authored notes are also incorporated there under `project-knowledge/`.

Use the installed Graphify skill for rebuilds and source-aware incremental updates after relevant changes. Run `graphify query "your question"` from the repository root, verify significant findings against source, and regenerate the local vault with `graphify export obsidian`. The graph uses directed edges so caller/callee relationships remain meaningful. Generated exports and caches stay local and are excluded from Git and extraction.

`POSTMORTEM.md` and `TEMPLATE.md` record the original Isaac deployment. Their network, image-permission, GPU, and process observations are historical evidence, not a fresh verification of every current image or RunPod configuration.
