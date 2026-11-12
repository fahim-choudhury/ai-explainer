---
name: explainer-video
description: Produce an animated explainer video end to end with review gates, using the ai-explainer-workflow repository. Use when the user wants a new explainer video on a topic, wants to continue, revise or review a stage of an existing explainer project (brief, research, script, narration, subtitles, visuals, render, YouTube package, social posts), or says "autopilot" for one.
---

# Explainer video

The workflow lives in the ai-explainer-workflow repository. This skill is installed as a symlink; resolve it with `readlink -f` and the repository root is four folders above the skill folder (`agents/claude/skills/explainer-video`).

1. Read `AGENTS.md` and `STYLE.md` in that repository and follow them exactly.
2. Run every `xv` command as `<repo>/bin/xv`.
