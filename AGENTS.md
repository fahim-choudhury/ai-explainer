# Explainer video workflow: instructions for AI agents

You produce an animated explainer video with the owner, from brief to YouTube and social packages, through review gates. Any agent that can run shell commands, read and write files, and fetch web pages can follow this file. The owner reviews at every gate, uploads and posts. Never upload, post or automate a platform account.

Paths below are relative to this repository unless they start with `<project>/`. The CLI is `bin/xv`, short for Xplainer Video. Video projects live in the workspace (`$XV_WORKSPACE`, or `workspace` in `xv.toml`, or `workspace/`), one folder per video: `explainer-<slug>/`. A project is a git repository.

## Before anything else

1. Run `bin/xv doctor --quick`. If it fails, tell the owner to run `./setup` and stop. Every xv command that touches a dependency refuses to run until `xv doctor` has passed.
2. Read [STYLE.md](STYLE.md). It governs every text you write in this workflow, including your messages to the owner.
3. Resuming a video: run `bin/xv status <project>` and do what its `Next` line says.
4. New video: run `bin/xv new <slug> "<Working title>"`, tell the owner the `<project>/inputs/` path for seed material, then start stage 0.

## Determinism rules

The same input must give the same output. Anything a command can do, a command does. Your judgment goes only into research, wording and visuals, and the commands check those too.

- Fix every `STALE` line from `xv status` before presenting.
- Never edit `STATUS.md` gates, the Stage line, Open feedback or Decisions by hand. Use `xv gate`, `xv feedback`, `xv decision`. `xv commit` sets the Stage line.
- Never write a commit message by hand in a project. `xv commit <project> <kind> "<summary>"` numbers versions from git history; `xv gate` commits approvals. Use kind `maintenance` for changes outside a stage.
- Never edit generated files: `script.md`, `timings.json`, `*.srt`, `asr-check.md`, `description.txt`, `upload-sheet.md`, `render/manifest.json`. Change the source and rerun the command. Notes for the upload sheet go in `<project>/publish/youtube/sheet-notes.md`.
- Run `xv lint <project>` before presenting any text. Errors block presenting. Fix each warning or name it in the review message with the reason it stays.
- Build each review message from `xv review <project>`: paste its output, then add only the list of changes since the last version and any open questions.
- When narration changes after gate 3, run `xv changed <project>` and give the owner its timestamps, so they can check those lines without rewatching.
- Use the defaults table below instead of choosing again per video. Record any departure with `xv decision`.
- Changes to this repository (lexicon, shared components, toolkit code) get their own commit here, separate from project commits. Run `.venv/bin/python -m pytest` and `xv doctor` afterwards.

### Defaults

| Choice | Default |
| --- | --- |
| Voice | Kokoro `af_heart`, speed 1.05 |
| Format | 16:9, 1080p30, -14 LUFS |
| Visual style | toolkit dark theme; neutral initial marks instead of logos (`<project>/video/src/brand.tsx`) |
| Thumbnails | `Thumbnail` and `ThumbnailB` Stills with different wording |
| YouTube category | 28, Science & Technology |
| A scene under 10 s at the end, such as a sources outro | chapter title `""`, which folds it into the previous chapter |
| Pronunciation fix | `say` map in `script.json`; never change the line text for the voice |
| Vendor comparison pages | cross-check only; a claim needs a second, primary source |
| Docs and code disagree | follow the code, record it in findings and with `xv decision` |

## Narration rules

On top of STYLE.md. `xv lint` enforces the rules marked with *:

- One idea per sentence, 25 words at most.* About 150 words per minute.
- Expand an acronym on first use unless the audience already knows it.* Declare each one in `script.json`: `acronyms` maps it to the expansion, which must appear in that line or a neighbouring one; `acronyms_known` lists those left unexpanded. For a beginner audience, add a short line that says what the thing does.
- No parentheses, slashes, URLs or symbols in narration.* Write numbers as words.*
- Each line in `script.json` is one subtitle cue and one animation beat. Split a line where the picture should change.

## Review messages

The owner may see only your last message of a turn. Each review message stands alone: the `xv review` output (absolute paths, lengths, check results), the changes since the last version, open questions, and how to approve. On approval, run `xv gate <project> <gate>`.

| Stage | Commit kind | Gate |
| --- | --- | --- |
| 0 Kickoff and brief | `brief` | `0` |
| 1 Research, 2 Script | `script` | `1-2` |
| 3 Narration | `narration` | `3` |
| 4 Visuals | `styleframes` | `4` |
| 5 Render | `render` | `5` |
| 6 YouTube | `youtube` | `6` |
| 7 Social | `social` | `7` |

A stage the brief excludes is skipped with `xv gate <project> 7 --skip "<reason from the brief>"`.

## Stages

### 0 Kickoff and brief

Ask the owner, in one message, with a recommended option first for each: purpose, audience, length and format, voice, visual style, must include or avoid, platforms, review mode. Use your agent's structured question tool if it has one. Recommend the defaults above. Fill `<project>/brief.md`, run `xv lint`, `xv commit <project> brief "..."`, `xv review`.

### 1 Research

- Read everything in `<project>/inputs/`. PDFs: `xv pdftext <file>`. Audio and video: `xv transcribe <file> --out <project>/inputs/notes/<name>.md`. Links in `links.md`: fetch each page.
- Then research on your own. Prefer primary sources in this order: source code, specs, official docs, vendor pages. For software, read the repository (a shallow `git clone` into a scratch folder, or the forge's API) to confirm how things work.
- Check the LICENSE of every repository a licence claim covers, not only the main one. Mobile apps often sit in separate repositories under a different licence.
- Docs lag behind code. When they disagree, follow the code and say so in findings.
- Log every source in `<project>/research/sources.md` as a numbered table row. Write `<project>/research/findings.md` organized by the questions the video must answer, citing `[#n]`. Mark anything unconfirmed UNVERIFIED and keep it out of the script; `xv review` counts these.
- Note where inputs disagree with primary sources and which one the script follows.

Research is reviewed together with the script.

### 2 Script and storyboard

- `<project>/script/script.json`: scenes with `id`, `title`, `lines`, plus `acronyms` and `acronyms_known`. Default arc: hook, problem, core idea, mechanism in steps, details the audience cares about, comparison, getting started, close. Fit it to the brief.
- `<project>/script/storyboard.md`: per scene and beat, what appears on screen.
- `xv script-md`, `xv lint`, `xv commit <project> script "..."`, `xv review`.
- If the owner edits `script.md` by hand, carry the edits into `script.json` and regenerate. Spellings that only help the voice, such as hyphens, go in `say` so the subtitles keep the plain text.

### 3 Narration and subtitles

- `xv synth` writes `audio/narration.wav`, `audio/timings.json` and `audio/<slug>.srt`. Lines are cached, so revisions only re-synthesize changed lines.
- `xv asr` transcribes each line with Whisper and writes `audio/asr-check.md`. For each flag, add a spoken form to `say` in `script.json` (project terms) or `lib/tts/lexicon.json` (general terms), or add the term to `asr_accept` when it sounds right. Rerun both until clean.
- Pacing is controlled by `speed` (1.0 to 1.1) and `gaps` in `script.json`.
- `xv commit <project> narration "..."`, `xv review`. List the lexicon entries added.
- A script edit after this gate means rerunning synth, which shifts every later timing. The scenes follow through beats, but recheck stills, and give the owner the `xv changed` timestamps.

### 4 Visual assets and styleframes

- Build scenes in `<project>/video/src/scenes.tsx` from the storyboard, with components imported from `@xv/ui` (`remotion/ui.tsx`). Every entrance is tied to a beat: `at={b[i] + n}`.
- Gather external assets into `<project>/assets/` and log each in `assets/ASSETS.md` with source and license. Do not use official logos or trademarks unless their brand guidelines allow it. Draw a neutral mark instead and note in the description that the video is independent.
- `xv typecheck`, then `xv stills` for one frame per scene, and `xv stills --per-beat` for dense scenes. Look at every contact sheet in `<project>/stills/` before presenting it. If you cannot view images, say so and ask the owner to check them.

Layout lessons:

- Text drawn over lines needs a background. Node labels already have one; give the same to any free text.
- Center long labels with a wide box and `whiteSpace: nowrap`. A narrow centered box overflows to one side.
- Keep content inside 120 px side margins, and below the title block, which ends near y = 250.
- Place curves and fallback paths so they pass through their node, not beside its label.
- Check that emoji render in stills. Prefer `Icon` glyphs.
- Give each product in a comparison its own colour and mark, including forks and reimplementations.
- Add a component to `remotion/ui.tsx` only when it is generic. Project-specific pieces go in `<project>/video/src/brand.tsx`.
- Every project imports the same `ui.tsx`. After changing an existing component there, run `xv stills` on the other projects and compare before committing. Adding new icons or components is safe.

### 5 Final render

- `xv render` renders `render/<slug>.mp4`, normalizes loudness to -14 LUFS, copies the srt beside it, writes `render/manifest.json`, and prints a QA summary.
- Check: duration matches the narration, both streams exist, and a stills pass on the final build shows no regressions.

### 6 YouTube package

- Fill `<project>/publish/youtube/metadata.json`: title of 70 characters or less with the search term first, description template with `{chapters}`, a chapter title for every scene id, tags.
- Description: opening paragraph on the viewer takeaway with the date facts were checked, chapters, primary source links, a not-affiliated note naming every company or project covered, a disclosure that narration is AI-generated, and trademark notes where needed.
- Thumbnails: edit `video/src/Thumbnail.tsx` and register each variant as a `<Still id="ThumbnailX">` in `Root.tsx`. `xv thumbnail` renders all of them.
- Write `publish/youtube/pinned-comment.txt`: the check date, an invitation to send corrections with a source, and one specific question.
- `xv youtube` writes `description.txt` and `upload-sheet.md`, including the thumbnail test line, and warns about chapter, title, size and missing-file problems. Fix every warning before presenting.

### 7 Social package

Read the "Social media" section of [GUIDE.md](GUIDE.md) and produce the files in `<project>/publish/social/` listed in its README:

- `plan.md`, a dated release schedule.
- `linkedin.md` and `xv carousel`.
- `thread.md` with X, Bluesky and Mastodon variants.
- `communities.md`, with the rules of each target community read and summarized.
- `article.md`.
- Shorts: `xv short <project> --start S --end E --name N --title "..."` for quick cuts, or a native 9:16 composition for the best one. Titles and descriptions go in `shorts/shorts.md`.

## Feedback loop

- Record each review item with `xv feedback <project> add "<item>"`. Address all of them, close each with `xv feedback <project> done <n>`, commit, and present the new version with a short list of what changed. `xv gate` refuses while items stay open.
- When feedback conflicts with a source, say so with the source and let the owner decide.
- Feedback that belongs to an earlier stage moves the project back to that stage. Rerun the stages after it.

## Autopilot

Triggered by "autopilot", "autopilot until <stage>" or "autopilot from <stage>".

- Skip the review stops in range. Self-review with `xv lint`, `xv status` and each stage's checks instead, and record every choice you would have asked about with `xv decision`.
- Kickoff on autopilot: take the defaults table, `brief.md`, and the owner's message. Record them as decisions.
- Choose the conservative option when unsure: fewer claims, primary sources only, no third-party logos.
- Always stop before anything outward-facing. Autopilot ends with the YouTube and social packages ready; the owner uploads and posts.
- Also stop when sources conflict on a fact the video depends on, or when a needed asset has no usable license.
- Finish with one review message: `xv review` output, the decisions list, flagged risks, and the files to open first.

## Commands

`<project>` is a folder name in the workspace, or a path.

| Command | Result |
| --- | --- |
| `xv doctor [--quick]` | verify every dependency against the lockfiles |
| `xv selftest` | throwaway project through synth, ASR, lint, typecheck and stills |
| `xv new <slug> "<title>"` | new project from `template/` |
| `xv status <project>` | stage, gates, open feedback, stale outputs, next step |
| `xv lint <project> [--only narration\|prose]` | narration rules and style checks; exit 1 on errors |
| `xv commit <project> <kind> "<summary>"` | commit as `<kind> vN: <summary>` |
| `xv gate <project> <gate> [--skip "<why>"]` | approve or skip a gate, set the stage, commit |
| `xv feedback <project> add "<item>" \| done <n> \| list` | Open feedback in STATUS.md |
| `xv decision <project> "<text>"` | Decisions in STATUS.md |
| `xv review <project> [<gate>]` | review package for the current stage |
| `xv changed <project> [--since <ref>]` | changed narration lines with new timestamps |
| `xv pdftext <file> [--out F]` | text of a PDF input |
| `xv transcribe <file> [--out F]` | Whisper transcript of an audio or video input |
| `xv script-md <project>` | `script/script.md` for review |
| `xv synth <project>` | narration, timings, srt |
| `xv asr <project> [--out <file>]` | `audio/asr-check.md` |
| `xv typecheck <project>` | TypeScript check of the scenes |
| `xv studio <project>` | Remotion Studio in the browser, for the owner |
| `xv stills <project> [--per-beat \| --frames a,b]` | stills and contact sheets |
| `xv render <project>` | `render/<slug>.mp4` and `render/manifest.json` |
| `xv thumbnail <project>` | every `Thumbnail*` Still as `publish/youtube/thumbnail*.jpg` |
| `xv youtube <project>` | `description.txt`, `upload-sheet.md` |
| `xv short <project> --start S --end E --name N --title T` | 9:16 cut in `publish/social/shorts/` |
| `xv carousel <project>` | `publish/social/linkedin-carousel.pdf` |
