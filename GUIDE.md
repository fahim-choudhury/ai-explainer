# Explainer video guide

This guide is for the owner: the person who reviews each video and publishes it. An AI agent writes, narrates, animates and renders each video and prepares the YouTube and social media material. You review at each gate, then upload and post yourself. The agent's own instructions are in [AGENTS.md](AGENTS.md).

## Quick start

1. Run `./setup` once. It downloads and verifies every dependency, then runs a self test. See [README.md](README.md) for the system tools it expects.
2. Choose where videos live: copy `xv.toml.example` to `xv.toml` and set `workspace`, or set `$XV_WORKSPACE`. The default is `workspace/` in this repository.
3. Start your agent in this repository and ask for an explainer video on a topic. It creates `explainer-<slug>/` in the workspace and asks the kickoff questions.
4. Drop seed material into `explainer-<slug>/inputs/`: notes, PDFs, images, audio, video, and links in `links.md`.
5. Review each stage when the agent presents it. Reply with feedback, "approved", or "autopilot".

To resume later, start the agent here and say "continue the <topic> explainer". It runs `xv status` and picks up where it stopped.

## Layout

```
ai-explainer/                this repository
  AGENTS.md                  instructions for the agent (CLAUDE.md and GEMINI.md point here)
  GUIDE.md                   this file
  STYLE.md                   writing rules for every text the agent produces
  setup                      installs and verifies every dependency
  bin/xv                     explainer video: command-line tool for every production step
  lib/                       xv code, Kokoro synthesis, Whisper check, lexicon.json, YouTube packager
  remotion/                  shared scene components (ui.tsx) and timeline (Explainer.tsx)
  template/                  skeleton copied for each new project
  deps/                      pinned tool and model downloads with SHA256 hashes
<workspace>/
  explainer-<slug>/
    STATUS.md                stage, gates, open feedback, decisions
    brief.md                 audience, purpose, length, voice, style, platforms
    inputs/                  your seed material (notes/, docs/, images/, media/, links.md)
    research/                sources.md (every source), findings.md (synthesis)
    script/                  script.json (narration), storyboard.md, script.md (review copy)
    audio/                   narration.wav, timings.json, <slug>.srt, asr-check.md
    assets/                  external images and clips, with ASSETS.md license log
    video/src/               scenes.tsx, Thumbnail.tsx, Root.tsx, brand.tsx (optional)
    stills/                  review frames and contact sheets
    render/                  <slug>.mp4, .srt, manifest.json
    publish/youtube/         metadata.json, description.txt, upload-sheet.md, thumbnail*.jpg
    publish/social/          plan, LinkedIn, thread, communities, article, shorts/
```

Each project is a git repository. The agent commits every version it presents, so `git log` and `git diff` show how the script or scenes changed between reviews.

## Stages and gates

| Stage | The agent produces | You review |
| --- | --- | --- |
| 0 Kickoff | `brief.md` from your answers | the brief |
| 1-2 Research and script | `sources.md`, `findings.md`, `script.json`, `storyboard.md`, `script.md` | `script.md` and `storyboard.md`; `findings.md` when a claim looks off |
| 3 Narration and subtitles | `narration.wav`, `<slug>.srt`, `asr-check.md` | listen to the wav, skim the srt |
| 4 Visuals | scenes, `assets/ASSETS.md`, contact sheets in `stills/` | the contact sheets |
| 5 Render | `render/<slug>.mp4` | the full video |
| 6 YouTube package | thumbnail, description, chapters, tags, `upload-sheet.md` | the sheet and thumbnail, then upload |
| 7 Social package | posts, thread, article, carousel, shorts, release plan | the copy, then post |

The order matters. Narration timing drives the animation, so the script is locked before audio, and audio is locked before visuals. Changing the script after stage 3 works, but the agent has to re-synthesize and recheck the visuals.

### Stage 0: kickoff

The agent asks about purpose, audience, length, voice, style, must-haves and platforms, then writes `brief.md`. A clear purpose helps most: who the video is for, and what it should help them do.

### Stages 1 and 2: research and script

The agent reads all of `inputs/`, researches on its own, and logs every source. Primary sources come first: official docs, specs, papers and source code. Unconfirmed claims stay out of the script.

The script is a list of scenes, and each scene is a list of narration lines. Each line becomes one subtitle and one animation beat. The storyboard says what appears on screen for each line. `script.md` is the readable version, with word count and estimated length.

Expect several rounds here. This stage costs the least to change.

### Stage 3: narration and subtitles

Kokoro reads each line. Whisper then transcribes the audio and flags lines where the voice said something other than the script, usually an acronym or a product name. The agent fixes these with spoken forms. "AWS" becomes "A-W-S" in the audio, while the subtitle keeps "AWS". General fixes go in `lib/tts/lexicon.json` and apply to every future project.

Whisper misses accent and emphasis problems, so listen once anyway. Tell the agent the timestamp and the word.

### Stage 4: visuals

The agent builds the scenes and shows you contact sheets: one frame per scene, or one per beat for busy scenes. Reviewing stills takes a minute; reviewing renders takes much longer. Point at problems by scene id and what you see: "connect: the relay label overlaps the curve".

To scrub through the animation, run `bin/xv studio explainer-<slug>` and open the browser tab.

### Stage 5: render

The agent renders the full video at 1080p30, normalizes loudness to the level YouTube plays at (-14 LUFS), and checks duration and streams. Give feedback as timestamps: "1:42, the chip appears before the voice mentions it".

### Stage 6: YouTube package

The agent prepares everything for a manual upload in YouTube Studio:

- `upload-sheet.md` lists every Studio field in order, with values and file paths.
- `description.txt` is ready to paste, chapters included.
- `thumbnail.jpg` comes with a variant or two for Studio's "Test & compare".
- `pinned-comment.txt` holds the comment to pin after publishing.

Custom thumbnails need a phone-verified channel (youtube.com/verify).

### Stage 7: social package

The agent writes the posts and cuts the clips. See [Social media](#social-media). You post.

## Reviewing and feedback

Reply in plain language. The agent records each item under `Open feedback` in `STATUS.md`, addresses all of them, commits, and sends the next version with a list of changes.

Useful forms:

- "approved", or "approved, but change X", which applies the change and moves on.
- Reference scene ids, line text or timestamps: "zerotrust, line 3: say 'one-way' instead of 'unidirectional'".
- "go back to the script": feedback that belongs to an earlier stage reopens it, and later stages are redone.
- "show me v2 vs v3": the agent diffs the versions from git.

## Autopilot

| You say | The agent does |
| --- | --- |
| "autopilot" | every remaining stage without stopping |
| "autopilot until audio" | runs through stage 3, then stops for review |
| "autopilot from visuals" | you reviewed up to audio; the agent finishes the rest |

On autopilot, the agent checks its own work at every gate. Each choice it would have asked about goes under `Decisions` in `STATUS.md`. When unsure, it takes the conservative option: fewer claims, primary sources, and no third-party logos.

Autopilot still stops when:

- the video and the YouTube and social packages are ready, since uploading and posting are yours;
- sources disagree on a fact the video depends on;
- a needed image or clip has no usable license.

The final message lists the video path, the decisions, and the files to open first.

## Toolkit commands

Add `bin/` to your PATH to type `xv` directly. `xv help` lists every command, and `xv help <command>` shows its options and examples. Every command accepts `-q` (quieter), `-d` (debug output) and `--no-color`.

| Command | Result |
| --- | --- |
| `xv new <slug> "<title>"` | new project `explainer-<slug>/` |
| `xv list` | your projects and the stage each one is at |
| `xv script-md <project>` | `script/script.md` with word count and estimated length |
| `xv synth <project>` | narration, timings and subtitles. Only changed lines are re-synthesized. |
| `xv asr <project>` | pronunciation report in `audio/asr-check.md` |
| `xv typecheck <project>` | checks the scene code |
| `xv studio <project>` | live preview in the browser |
| `xv stills <project>` | one frame per scene plus contact sheets (`--per-beat` for one frame per line) |
| `xv render <project>` | final video, loudness-normalized |
| `xv thumbnail <project>` | 1280x720 thumbnail |
| `xv youtube <project>` | `description.txt` and `upload-sheet.md` |
| `xv short <project> --start 182 --end 222 --name mobile --title "NetBird on mobile"` | 9:16 clip with burned-in captions |
| `xv carousel <project>` | scene stills as a PDF for LinkedIn |
| `xv status <project>` | stage, gates, open feedback, outputs that are out of date, and the next step |
| `xv lint <project>` | narration rules (line length, numbers, symbols, acronyms) and writing checks |
| `xv review <project>` | the review package for the current stage |
| `xv changed <project>` | narration lines changed since the last script commit, with their new timestamps |
| `xv commit`, `xv gate`, `xv feedback`, `xv decision` | the only way STATUS.md and project commits change |
| `xv doctor` | checks every dependency against the lockfiles; other commands refuse to run until it passes |
| `xv selftest` | runs a throwaway project through synthesis, the Whisper check, linting and stills |
| `xv pdftext`, `xv transcribe` | text from PDF, audio and video inputs |

The agent runs every step through these commands, so the same script, settings and toolkit version give the same files. The agent's own judgment goes into research, wording and visuals, and `xv lint` checks the wording.

Voice options for `script.json`: `af_heart`, `af_bella`, `am_michael`, `am_fenrir`, `bf_emma`, `bm_george`, and others in the Kokoro voice list. `speed` between 1.0 and 1.1 sounds natural.

## Social media

Each video gets a release plan in `publish/social/plan.md`. The ideas below are the playbook the agent draws from.

### Release week

| Day | Post |
| --- | --- |
| Release day, Tuesday to Thursday morning | YouTube public, comment pinned, added to its playlist. LinkedIn post with native video. X, Bluesky and Mastodon threads. |
| Day 1 | First Short on YouTube Shorts, Instagram Reels and TikTok |
| Day 2 or 3 | Companion article on Dev.to or Hashnode, with the video embedded |
| Days 3 to 5 | Community posts, one per community, spaced apart |
| Day 7 | Second Short, and the LinkedIn carousel |
| Day 14 | Third Short. Review the numbers in Studio and record them in `plan.md`. |

### YouTube

- Group related videos into playlists, such as "Networking explained" for NetBird, WireGuard and zero trust. Link them with end screens.
- Keep the thumbnail style the same across a series so viewers recognize it. Use Studio's "Test & compare" with the variants.
- The pinned comment asks a specific question about the topic, which gets more replies than a general request for comments.
- Once a video has a few weeks of data, read the retention graph. The first big drop shows a weak hook or a slow section. Fix that in the next script.

### LinkedIn

- Upload a 60 to 90 second cut natively, with burned-in captions, since many people watch muted. Put the YouTube link in the first comment.
- The first two lines show before "see more", so open with the problem the video solves. Write in your own voice: what you learned making it, and one specific technical detail.
- The carousel (`xv carousel`) is a document post of the scene stills, one idea per page. It suits diagram-heavy topics.
- Tag the company or project page when you cover one.

### Shorts, Reels and TikTok

- One idea per short, 30 to 60 seconds, with the hook in the first two seconds. Self-contained segments work best, such as "how two peers connect" or "NetBird on mobile".
- `xv short` makes a quick cut: the 16:9 video centered on a blurred background, with a title and captions. For the best short of each video, ask the agent for a native 9:16 composition. The diagrams are then laid out for a phone screen and read better.
- Upload the same file to all three platforms. On YouTube Shorts, set the full video as the related video.

### X, Bluesky and Mastodon

- A thread of four to six posts: the problem, a 30 to 60 second clip, a key diagram or two as images, and the link last.
- Length limits differ: X 280 characters (free accounts), Bluesky 300, Mastodon 500. `thread.md` has a variant for each.
- Mastodon discovery runs on hashtags. Use CamelCase (#ZeroTrust) so screen readers pronounce them.
- Add alt text to every image.

### Communities

- Reddit: pick communities where the topic is on-topic (for NetBird: r/selfhosted, r/homelab, r/networking, r/WireGuard). Read each community's self-promotion rules first; many allow it only in a weekly thread. Post the summary and the most useful diagram in the body, say the video is yours, and stay to answer comments.
- Hacker News: videos rarely do well there. Submit the companion article, and only when it has substance a reader cannot get from the docs. Never ask for upvotes.
- Dev.to, Hashnode and Medium: `article.md` is the script reworked for reading, with diagrams and the embedded video. Set the canonical URL to the first place you publish it.
- Project communities (Slack, Discord, GitHub Discussions): ask a maintainer before posting. Maintainers often share accurate explainers about their project.
- If a video supports a job application, send it directly to the hiring team or recruiter instead of waiting for reach.

### Measuring

Record these in `plan.md` after a week and after a month:

- YouTube: impressions click-through rate, average view duration, retention drop points, and subscribers gained.
- Each platform: views, comments, and clicks through to YouTube.

Carry the lessons into the next brief.

## Maintaining the toolkit

- Pronunciation fixes that apply beyond one video go in `lib/tts/lexicon.json`.
- Generic visual components go in `remotion/ui.tsx`, which every project shares through the `@xv/` import alias. Project-specific pieces, such as a product wordmark, live in that project's `video/src/brand.tsx`. Changing an existing component changes every video at its next render, so the agent checks stills of the other projects after such a change.
- Every dependency is pinned: Python packages in `uv.lock`, the Python and uv versions in `deps/tools.json`, Node packages in `package-lock.json`, models in `deps/models.json`. To upgrade one, change its pin, run `./setup`, then `xv selftest` and a render of an existing project.
- Remotion versions move together: change every `@remotion/*` and `remotion` entry at once.
- Each toolkit change gets its own commit in this repository, so `git log` shows when shared behaviour changed. Run `.venv/bin/python -m pytest` before committing.
- Generated files (`script.md`, `description.txt`, `upload-sheet.md` and others) are rewritten on every run. Put upload-sheet notes in `publish/youtube/sheet-notes.md`.
