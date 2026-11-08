# Repository Agent Guidelines: mc-zynthian

## Documentation Standards & Separation of Concerns

All agents working on this repository must strictly adhere to the following rules regarding documentation and project configuration:

### 1. Factual & Verified Technical Documentation Only (`docs/`)
- All files in the `docs/` directory must contain exclusively factual, correct, and verifiable documentation.
- Information must be derived strictly from official vendor manuals, source code, data sheets, or empirical experiments verified during development.

### 2. Permitted Content in `docs/`
- Hardware and software technical specifications, pinouts, and timing constraints.
- Architecture explanations, communication protocols, and how subsystems work.
- General configuration methods, syntax, and how-to guides.
- Troubleshooting matrices, root cause analysis, and configuration challenges encountered that assist future debugging.

### 3. Absolute Ban on Setup-Specific Configurations in `docs/`
- **Zero Setup-Specific Configurations in `docs/`:** Documentation files must NEVER contain configurations specific to this physical build. This includes:
  - Macro pad key layouts (e.g., assigning specific actions to specific keys like Key A, B, C, D, E, F).
  - Specific LED colors, lighting modes, or layer numbers chosen for this particular setup.
  - Setup-specific channel assignments or personal routing schemes.
- **Single Source of Truth (`README.md`):** All configurations, active keybindings, layer profiles, and hardware setup logs specific to this project build belong exclusively in [`README.md`](README.md).
- **No Duplication:** Never duplicate information between `docs/` and `README.md`. `docs/` holds the reference manuals; `README.md` holds this setup's implementation.

### 4. Sources and External Links Only (No Project File Lists)
- Each document in `docs/` must conclude with a list of external source links, references, and citations used to compile that guide.
- **No Internal Project File Lists:** Reference sections must NEVER include a list of other project files (e.g., cross-linking other `docs/*.md` guides or `README.md` as "project ecosystem" lists). This prevents circular cross-referencing and redundant duplication.
