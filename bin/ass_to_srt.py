#!/usr/bin/env python3
"""Convert ASS subtitle files to clean SRT files.

For each input ASS file, this script:
1. Converts to SRT using ffmpeg.
2. Merges consecutive entries that share the same timestamp into one entry.
3. Re-numbers all entries sequentially.
4. Ensures the output is clean UTF-8 without BOM or extraneous characters.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def convert_ass_to_srt(ass_path: Path) -> Path:
    """Run ffmpeg to convert an ASS file to SRT, returning the SRT path."""
    srt_path = ass_path.with_suffix(".srt")
    cmd = ["ffmpeg", "-y", "-i", str(ass_path), "-c:s", "srt", str(srt_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error converting {ass_path}:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    return srt_path


def parse_srt(text: str) -> list[dict]:
    """Parse SRT text into a list of entries with 'timestamp' and 'text' keys."""
    entries = []
    # Split into blocks separated by blank lines
    blocks = re.split(r"\n\n+", text.strip())
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 2:
            continue
        # First line is the index (ignored, we'll re-number later)
        # Second line is the timestamp
        timestamp = lines[1].strip()
        # Remaining lines are the subtitle text
        subtitle_text = "\n".join(lines[2:]).strip()
        if timestamp and subtitle_text:
            entries.append({"timestamp": timestamp, "text": subtitle_text})
    return entries


def merge_consecutive_same_timestamps(entries: list[dict]) -> list[dict]:
    """Merge consecutive entries that share the same timestamp."""
    if not entries:
        return []

    merged = [entries[0].copy()]
    for entry in entries[1:]:
        if entry["timestamp"] == merged[-1]["timestamp"]:
            merged[-1]["text"] += "\n" + entry["text"]
        else:
            merged.append(entry.copy())
    return merged


def build_srt(entries: list[dict]) -> str:
    """Build a properly numbered SRT string from a list of entries."""
    parts = []
    for i, entry in enumerate(entries, start=1):
        parts.append(f"{i}\n{entry['timestamp']}\n{entry['text']}\n")
    return "\n".join(parts) + "\n"


def clean_text(text: str) -> str:
    """Remove BOM and other extraneous characters from the text."""
    # Strip UTF-8 BOM
    text = text.lstrip("\ufeff")
    # Remove carriage returns (normalize to Unix line endings)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Strip <font ...> and </font> tags (styling from ASS, not useful in SRT)
    text = re.sub(r"<font[^>]*>", "", text)
    text = text.replace("</font>", "")
    # Remove ASS formatting tags that ffmpeg may leave behind, e.g. {\an8}
    text = re.sub(r"\{\\[^}]*\}", "", text)
    return text


def process_file(ass_path: Path) -> None:
    """Full pipeline for a single ASS file."""
    print(f"Processing {ass_path} ...")

    # Step 1: Convert ASS -> SRT via ffmpeg
    srt_path = convert_ass_to_srt(ass_path)

    # Step 2: Read and clean the SRT content
    raw = srt_path.read_text(encoding="utf-8-sig")  # handles BOM transparently
    text = clean_text(raw)

    # Step 3: Parse, merge, re-number
    entries = parse_srt(text)
    merged = merge_consecutive_same_timestamps(entries)
    output = build_srt(merged)

    # Step 4: Write clean UTF-8 (no BOM)
    srt_path.write_text(output, encoding="utf-8")
    print(f"  -> {srt_path}  ({len(entries)} entries merged to {len(merged)})")


def main():
    parser = argparse.ArgumentParser(
        description="Convert ASS subtitle files to clean, merged SRT files."
    )
    parser.add_argument(
        "files",
        nargs="+",
        type=Path,
        metavar="FILE",
        help="One or more ASS subtitle files to convert (glob patterns are expanded by the shell).",
    )
    args = parser.parse_args()

    for filepath in args.files:
        if not filepath.exists():
            print(f"Warning: {filepath} not found, skipping.", file=sys.stderr)
            continue
        if filepath.suffix.lower() != ".ass":
            print(f"Warning: {filepath} is not an .ass file, skipping.", file=sys.stderr)
            continue
        process_file(filepath)


if __name__ == "__main__":
    main()
