# TSA 3D Monster Agent Bootstrap

## Mandatory startup

The Agent runs in WSL Ubuntu 24.04. Blender runs as native Windows Blender 5.2, never Linux Blender.

Before future work read: (1) `AGENTS.md`, (2) `TSA_MONSTER_KNOWLEDGE.md`, and (3) `TSA_MONSTER_STATE.md`. Do not full-scan the repository unless explicitly required. Read only the current state's referenced artifacts and task-relevant files.

## TSA workflow

- Goal first; incremental work; small dependency cone.
- Preserve the accepted baseline; fail closed; validate actual behavior.
- Stop at the iteration boundary and never auto-continue.
- Previous accepted iteration artifacts are immutable.
- Visual evidence takes precedence over shallow boolean PASS claims.

## Environment

- Windows root: `C:\Users\HWI-ADMIN\Downloads\3d\`
- WSL root: `/mnt/c/Users/HWI-ADMIN/Downloads/3d/`
- Windows Blender: `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`
- From WSL: `/mnt/c/Program Files/Blender Foundation/Blender 5.2/blender.exe`

Do not install Blender Linux or move the project into WSL. Always update State after a successful or blocked iteration. Update Knowledge only for durable verified facts; never record guesses.
