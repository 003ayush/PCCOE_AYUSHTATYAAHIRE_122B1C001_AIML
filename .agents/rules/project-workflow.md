# Project Workflow Rules

## 1. Approval gate
- NEVER write code, create project files, install packages, or run setup commands until the user has explicitly approved my understanding and the plan.
- Order of work: requirements -> plan -> user approval -> code.
- When unsure whether to proceed, ask. Discussion requests mean discuss only.

## 2. Transparency and Origin (Never assume knowledge)
- Never assume the user knows everything. 
- When generating data, providing solutions, or pulling from research, explicitly state *how* and *where* you got the information.
- Example: If creating synthetic data, explain which real-world standards (e.g., UN R155, STRIDE) or search results were used to build it.

## 3. Coding standards
- Prefer concise, idiomatic code. If a built-in, library function, or method does the job in a few lines, use it instead of long manual code.
- Avoid reinventing utilities. Keep functions small and reusable.
- Add proper comments and docstrings: explain purpose and non-obvious logic.

## 4. Documentation upkeep
- Always update README.md (setup, usage, architecture) when behavior or structure changes.
- Always update CONTEXT.md, which holds the current status of the application: what is done, in progress, next, and key decisions.
- Update both in the same change as the code, never later.
