"""Build the manual-upload package for YouTube Studio. No network access, no API.

Usage:  xv youtube <project>

Reads   <project>/publish/youtube/metadata.json, audio/timings.json
Writes  <project>/publish/youtube/description.txt   (paste into Studio)
        <project>/publish/youtube/upload-sheet.md   (every field to fill in, in Studio order)

Both files are regenerated on every run, so never edit them by hand. Extra notes for the
sheet go in publish/youtube/sheet-notes.md, which is appended verbatim.
"""
import json, sys
from pathlib import Path

CATEGORIES = {"27": "Education", "28": "Science & Technology", "22": "People & Blogs"}


def chapters(proj, titles):
    t = json.loads((proj / "audio/timings.json").read_text())
    lines, warn = [], []
    ids = [s["id"] for s in t["scenes"]]
    for k in ids:
        if k not in titles:
            warn.append(f"chapter_titles has no entry for scene '{k}' (the id is used as the title)")
    for k in titles:
        if k not in ids:
            warn.append(f"chapter_titles names unknown scene '{k}'")
    for i, s in enumerate(t["scenes"]):
        title = titles.get(s["id"], s["id"])
        if title == "" and i > 0:  # empty title folds the scene into the previous chapter
            continue
        sec = 0 if i == 0 else int(s["start"])
        lines.append(f"{sec // 60}:{sec % 60:02d} {title}")
        nxt = next((x for x in t["scenes"][i + 1:] if titles.get(x["id"], x["id"]) != ""), None)
        end = nxt["start"] if nxt else t["total"]
        if end - s["start"] < 10:
            warn.append(f"chapter '{s['id']}' is under 10 s")
    if len(lines) < 3:
        warn.append("fewer than 3 chapters")
    return "\n".join(lines), warn


def main(proj):
    proj = Path(proj).resolve()
    pub = proj / "publish/youtube"
    meta = json.loads((pub / "metadata.json").read_text())
    slug = json.loads((proj / "script/script.json").read_text())["slug"]
    chap, warn = chapters(proj, meta.get("chapter_titles", {}))
    desc = meta["description_template"].replace("{chapters}", chap)

    title = meta["title"]
    if not 0 < len(title) <= 100:
        warn.append(f"title must be 1-100 characters (now {len(title)})")
    if len(desc.encode()) > 5000:
        warn.append("description over 5000 bytes")
    if "<" in desc or ">" in desc:
        warn.append("description contains < or >, which YouTube rejects")
    tags = ", ".join(meta.get("tags", []))
    if len(tags) > 500:
        warn.append("tags over 500 characters")
    thumb = pub / "thumbnail.jpg"
    variants = sorted(f for f in pub.glob("thumbnail-*.jpg"))
    for v in variants:
        if v.stat().st_size > 2 * 1024 * 1024:
            warn.append(f"{v.name} over 2 MB")
    if not (pub / "pinned-comment.txt").exists():
        warn.append("no pinned-comment.txt")
    srt = proj / f"render/{slug}.srt"
    if not srt.exists():
        srt = proj / f"audio/{slug}.srt"
    if not thumb.exists():
        warn.append("no thumbnail.jpg: run `xv thumbnail`")
    elif thumb.stat().st_size > 2 * 1024 * 1024:
        warn.append("thumbnail over 2 MB")
    video = proj / f"render/{slug}.mp4"
    if not video.exists():
        warn.append(f"no render/{slug}.mp4: run `xv render`")

    (pub / "description.txt").write_text(desc)
    sheet = f"""# YouTube upload sheet: {title}

Upload at https://studio.youtube.com -> Create -> Upload videos.

| Field | Value |
| --- | --- |
| File | `{video}` |
| Title | {title} |
| Description | paste `description.txt` (chapters included) |
| Thumbnail | `{thumb}` |
| Audience | {"Made for kids" if meta.get("madeForKids") else "No, it's not made for kids"} |
| Tags (Show more) | {tags} |
| Language | {meta.get("defaultLanguage", "en")} |
| Category | {CATEGORIES.get(meta.get("categoryId", "28"), meta.get("categoryId"))} |
| Altered or synthetic content | No (AI narration is disclosed in the description) |
| Subtitles | Add language -> English -> Upload file -> With timing -> `{srt}` |
| End screen | Video elements -> End screen: link the next video or playlist over the last 20 s |
| Visibility | {meta.get("visibility", "Public, or Schedule for the release slot in publish/social/plan.md")} |

After publishing: add the video to its playlist, pin the comment from `{pub / "pinned-comment.txt"}`, and put the URL in `publish/social/plan.md`.
"""
    if variants:
        sheet += ("\nThumbnail test: in Studio, Test & compare -> add " +
                  ", ".join(f"`{v}`" for v in variants) + (" as the second option.\n" if len(variants) == 1 else " as further options.\n"))
    notes = pub / "sheet-notes.md"
    if notes.exists():
        sheet += "\n" + notes.read_text().rstrip() + "\n"
    (pub / "upload-sheet.md").write_text(sheet)
    print(f"wrote {pub / 'description.txt'}\nwrote {pub / 'upload-sheet.md'}")
    for w in warn:
        print("WARNING:", w)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
