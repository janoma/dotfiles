#!/usr/bin/env python3
"""Remux YouTube downloads into dated, cleaned MP4 files.

For each video in a directory, this script:
1. Reads the YouTube URL from the file's comment metadata.
2. Looks up the publish date with the YouTube Data API.
3. Builds an ASCII title from the filename.
4. Downloads one subtitle track per requested language.
5. Writes a new MP4 beside the original. The original stays in place.

Uploader-provided subtitles are preferred over automatic captions. A locale
such as en-US is only used to find a track. The MP4 stores the ISO 639-2
language with no region, so en becomes eng.

Install:
    pip install unidecode
    brew install homebrew-ffmpeg/ffmpeg/ffmpeg --with-libsoxr
    brew install yt-dlp

Set YOUTUBE_API_KEY to a YouTube Data API key. Titles are not sent to Google.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    from unidecode import unidecode
except ImportError:  # pragma: no cover - exercised only when the package is missing
    unidecode = None


VIDEO_EXTENSIONS = {".mkv", ".mp4", ".webm", ".mov", ".m4v", ".avi"}
API_BATCH_SIZE = 50
ENCODE_VIDEO = ["-c:v", "libx265", "-crf", "20", "-preset", "ultrafast", "-tag:v", "hvc1"]

# Genre labels removed only when they are a short prefix before a separator,
# or the whole contents of a leading [bracket] or (parenthesis).
CATEGORIES = frozenset({
    "analysis",
    "audiobook",
    "clip",
    "clips",
    "commentary",
    "concert",
    "conference",
    "course",
    "debate",
    "discussion",
    "documentaries",
    "documentary",
    "episode",
    "essay",
    "explainer",
    "featurette",
    "film",
    "gameplay",
    "guide",
    "highlights",
    "interview",
    "interviews",
    "keynote",
    "lecture",
    "lectures",
    "lesson",
    "live",
    "movie",
    "news",
    "panel",
    "performance",
    "podcast",
    "podcasts",
    "presentation",
    "reaction",
    "reactions",
    "recap",
    "review",
    "reviews",
    "series",
    "sermon",
    "short",
    "shorts",
    "show",
    "speech",
    "talk",
    "talks",
    "trailer",
    "trailers",
    "tutorial",
    "tutorials",
    "unboxing",
    "vlog",
    "vlogs",
    "walkthrough",
    "webinar",
})

TECHNICAL = frozenset({
    "2160p",
    "1440p",
    "1080p",
    "720p",
    "480p",
    "360p",
    "240p",
    "4320p",
    "4k",
    "8k",
    "x264",
    "x265",
    "h264",
    "h265",
    "h.264",
    "h.265",
    "hevc",
    "avc",
    "av1",
    "vp8",
    "vp9",
    "aac",
    "opus",
    "mp3",
    "ac3",
    "eac3",
    "dts",
    "dts-hd",
    "truehd",
    "flac",
    "atmos",
    "web-dl",
    "webrip",
    "bluray",
    "blu-ray",
    "bdrip",
    "brrip",
    "hdtv",
    "dvdrip",
    "hdrip",
    "remux",
    "hdr",
    "sdr",
    "10bit",
    "8bit",
    "10-bit",
    "8-bit",
    "60fps",
    "30fps",
    "24fps",
    "25fps",
    "50fps",
    "5.1",
    "7.1",
    "2.0",
})

# ISO 639-1 (and a few deprecated codes YouTube still emits) to the
# bibliographic ISO 639-2 code the MP4 muxer actually stores.
_ISO639_2 = {
    "aa": "aar", "ab": "abk", "ae": "ave", "af": "afr", "ak": "aka", "am": "amh",
    "an": "arg", "ar": "ara", "as": "asm", "av": "ava", "ay": "aym", "az": "aze",
    "ba": "bak", "be": "bel", "bg": "bul", "bh": "bih", "bi": "bis", "bm": "bam",
    "bn": "ben", "bo": "tib", "br": "bre", "bs": "bos", "ca": "cat", "ce": "che",
    "ch": "cha", "co": "cos", "cr": "cre", "cs": "cze", "cu": "chu", "cv": "chv",
    "cy": "wel", "da": "dan", "de": "ger", "dv": "div", "dz": "dzo", "ee": "ewe",
    "el": "gre", "en": "eng", "eo": "epo", "es": "spa", "et": "est", "eu": "baq",
    "fa": "per", "ff": "ful", "fi": "fin", "fj": "fij", "fo": "fao", "fr": "fre",
    "fy": "fry", "ga": "gle", "gd": "gla", "gl": "glg", "gn": "grn", "gu": "guj",
    "gv": "glv", "ha": "hau", "he": "heb", "hi": "hin", "ho": "hmo", "hr": "hrv",
    "ht": "hat", "hu": "hun", "hy": "arm", "hz": "her", "ia": "ina", "id": "ind",
    "ie": "ile", "ig": "ibo", "ii": "iii", "ik": "ipk", "in": "ind", "io": "ido",
    "is": "ice", "it": "ita", "iu": "iku", "iw": "heb", "ja": "jpn", "ji": "yid",
    "jv": "jav", "jw": "jav", "ka": "geo", "kg": "kon", "ki": "kik", "kj": "kua",
    "kk": "kaz", "kl": "kal", "km": "khm", "kn": "kan", "ko": "kor", "kr": "kau",
    "ks": "kas", "ku": "kur", "kv": "kom", "kw": "cor", "ky": "kir", "la": "lat",
    "lb": "ltz", "lg": "lug", "li": "lim", "ln": "lin", "lo": "lao", "lt": "lit",
    "lu": "lub", "lv": "lav", "mg": "mlg", "mh": "mah", "mi": "mao", "mk": "mac",
    "ml": "mal", "mn": "mon", "mo": "rum", "mr": "mar", "ms": "may", "mt": "mlt",
    "my": "bur", "na": "nau", "nb": "nob", "nd": "nde", "ne": "nep", "ng": "ndo",
    "nl": "dut", "nn": "nno", "no": "nor", "nr": "nbl", "nv": "nav", "ny": "nya",
    "oc": "oci", "oj": "oji", "om": "orm", "or": "ori", "os": "oss", "pa": "pan",
    "pi": "pli", "pl": "pol", "ps": "pus", "pt": "por", "qu": "que", "rm": "roh",
    "rn": "run", "ro": "rum", "ru": "rus", "rw": "kin", "sa": "san", "sc": "srd",
    "sd": "snd", "se": "sme", "sg": "sag", "si": "sin", "sk": "slo", "sl": "slv",
    "sm": "smo", "sn": "sna", "so": "som", "sq": "alb", "sr": "srp", "ss": "ssw",
    "st": "sot", "su": "sun", "sv": "swe", "sw": "swa", "ta": "tam", "te": "tel",
    "tg": "tgk", "th": "tha", "ti": "tir", "tk": "tuk", "tl": "tgl", "tn": "tsn",
    "to": "ton", "tr": "tur", "ts": "tso", "tt": "tat", "tw": "twi", "ty": "tah",
    "ug": "uig", "uk": "ukr", "ur": "urd", "uz": "uzb", "ve": "ven", "vi": "vie",
    "vo": "vol", "wa": "wln", "wo": "wol", "xh": "xho", "yi": "yid", "yo": "yor",
    "za": "zha", "zh": "chi", "zu": "zul",
}

_VIDEO_ID = r"[0-9A-Za-z_-]{11}"
_URL_PATTERNS = (
    re.compile(rf"(?:https?://)?(?:www\.|m\.)?youtube\.com/watch\?[^\s\"']*?v=({_VIDEO_ID})(?![0-9A-Za-z_-])", re.IGNORECASE),
    re.compile(rf"(?:https?://)?youtu\.be/({_VIDEO_ID})(?![0-9A-Za-z_-])", re.IGNORECASE),
    re.compile(rf"(?:https?://)?(?:www\.|m\.)?youtube\.com/(?:embed|shorts|live|v)/({_VIDEO_ID})(?![0-9A-Za-z_-])", re.IGNORECASE),
    re.compile(rf"(?:https?://)?music\.youtube\.com/watch\?[^\s\"']*?v=({_VIDEO_ID})(?![0-9A-Za-z_-])", re.IGNORECASE),
)
_CATEGORY_WORDS = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?")
_LEADING_WRAPPER = re.compile(r"^[\[\(]([^\[\]()]*)[\]\)]\s*(.*)$")
_LEADING_LABEL = re.compile(r"^(.+?)\s*(?:\||:|\s[-\u2013\u2014]\s)\s*(.+)$")
_BRACKET_GROUP = re.compile(r"[\[\(]([^\[\]()]*)[\]\)]")
_DOTTED_PART = re.compile(r"\d+\.\d+|[^.]+")
_TOKEN = re.compile(r"\d+\.\d+|[hx]\.26[45]|[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", re.IGNORECASE)
_STANDALONE_TOKEN = re.compile(
    r"(?<!\S)(?:\d+\.\d+|[hx]\.26[45]|[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)(?!\S)",
    re.IGNORECASE,
)
_TRAILING_ID = re.compile(
    rf"(?:\s*[\[\(](?P<bracket>{_VIDEO_ID})[\]\)]|\s+(?P<bare>{_VIDEO_ID}))\s*$"
)
_TITLE_PUNCTUATION = set("&',-.!?()")


def extract_video_id(text: str) -> str | None:
    """Return the first YouTube video id found in text, or None."""
    if not text:
        return None
    found: tuple[int, str] | None = None
    for pattern in _URL_PATTERNS:
        match = pattern.search(text)
        if match is not None and (found is None or match.start() < found[0]):
            found = (match.start(), match.group(1))
    return None if found is None else found[1]


def parse_languages(spec: str) -> list[str]:
    """Split a comma-separated locale list into base language codes, in order.

    en-US and en-GB both become en, and the second English entry is dropped.
    """
    seen: set[str] = set()
    languages: list[str] = []
    for raw in spec.split(","):
        token = raw.strip()
        if not token:
            continue
        base = token.split("-", 1)[0].strip().lower()
        if not re.fullmatch(r"[a-z]{2,3}", base):
            print(f"Warning: ignoring subtitle locale {token!r}.", file=sys.stderr)
            continue
        if base in seen:
            continue
        seen.add(base)
        languages.append(base)
    return languages


def strip_title(name: str) -> str:
    """Turn a filename stem into an ASCII title.

    Emoji and decorative marks are removed before transliteration. A short
    leading category (all-caps, or a known label) is removed when a separator
    or wrapper sets it apart from the title. Codec and release tokens are
    removed only when they stand alone or fill a bracket group.
    """
    if unidecode is None:
        raise SystemExit("Missing Python package unidecode. Install it with: pip install unidecode")

    text = unicodedata.normalize("NFKC", name)
    text = "".join(char for char in text if not _is_dropped_char(char))
    text = unidecode(text)
    text = _strip_categories(text)
    text = _strip_technical(text)
    text = _strip_trailing_video_id(text)
    text = _finalize_title(text)
    text = _strip_standalone_technical(text)
    return _finalize_title(text)


def local_calendar_date(moment: datetime) -> str:
    """Format a UTC timestamp as the computer's local calendar date."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone().date().isoformat()


def list_videos(directory: Path) -> list[Path]:
    """Return video files directly inside directory, ignoring subdirectories."""
    files = [
        path for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    ]
    return sorted(files, key=lambda path: path.name)


def read_comment(path: Path) -> str:
    """Return the comment tag from a media file, or an empty string."""
    command = [
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_entries", "format_tags",
        str(path),
    ]
    result = _run(command)
    if result.returncode != 0:
        detail = result.stderr.strip() or "ffprobe failed"
        raise RuntimeError(detail)
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ffprobe returned invalid JSON: {exc}") from exc
    tags = (payload.get("format") or {}).get("tags") or {}
    for key, value in tags.items():
        if key.lower() == "comment" and isinstance(value, str):
            return value
    return ""


def fetch_published_dates(video_ids: list[str], api_key: str) -> dict[str, datetime]:
    """Look up snippet.publishedAt for video ids, in batches of 50."""
    published: dict[str, datetime] = {}
    unique = list(dict.fromkeys(video_ids))
    for start in range(0, len(unique), API_BATCH_SIZE):
        chunk = unique[start:start + API_BATCH_SIZE]
        params = urllib.parse.urlencode({
            "part": "snippet",
            "id": ",".join(chunk),
            "key": api_key,
        })
        url = f"https://www.googleapis.com/youtube/v3/videos?{params}"
        request = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip()
            raise SystemExit(f"YouTube API error {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise SystemExit(f"YouTube API request failed: {exc.reason}") from exc
        for item in payload.get("items", []):
            video_id = item.get("id")
            raw = ((item.get("snippet") or {}).get("publishedAt"))
            if not video_id or not raw:
                continue
            published[video_id] = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    return published


def claim_destination(
    directory: Path,
    day: str,
    title: str,
    video_id: str,
    claimed: set[Path],
) -> Path | None:
    """Pick an unused MP4 path, or None when that name is already taken."""
    dest = directory / f"{day} {title}.mp4"
    if dest in claimed:
        dest = directory / f"{day} {title} [{video_id}].mp4"
    if dest.exists() or dest in claimed:
        return None
    claimed.add(dest)
    return dest


def download_subtitles(
    video_id: str,
    languages: list[str],
    tmp: Path,
    ytdlp: str,
) -> list[tuple[Path, str]]:
    """Download one SRT per language. Manual tracks win over automatic ones."""
    selected: list[tuple[Path, str]] = []
    for language in languages:
        path = _download_language(video_id, language, tmp / language, ytdlp)
        if path is None:
            print(f"  no {language} subtitles")
            continue
        selected.append((path, language))
    return selected


def build_ffmpeg_command(
    src: Path,
    subtitles: list[tuple[Path, str]],
    dest: Path,
    encode: bool,
) -> list[str]:
    """Build an ffmpeg command that copies streams into an MP4 container.

    Subtitles already in the source are not mapped. Downloaded SRTs are
    encoded as mov_text and tagged with the base language code.
    """
    command = ["ffmpeg", "-y", "-nostdin", "-i", str(src)]
    for subtitle, _language in subtitles:
        command.extend(["-i", str(subtitle)])
    command.extend(["-map", "0:v", "-map", "0:a?"])
    for index in range(len(subtitles)):
        command.extend(["-map", f"{index + 1}:0"])
    if encode:
        command.extend(ENCODE_VIDEO)
        command.extend(["-c:a", "copy"])
    else:
        command.extend(["-c", "copy"])
    if subtitles:
        command.extend(["-c:s", "mov_text"])
    command.extend(["-map_metadata", "0"])
    for index, (_subtitle, language) in enumerate(subtitles):
        command.extend([f"-metadata:s:s:{index}", f"language={_mp4_language(language)}"])
    # The temporary path ends in .mp4.part, so the container has to be named.
    command.extend(["-f", "mp4", str(dest)])
    return command


def _mp4_language(code: str) -> str:
    """Map a base language to the ISO 639-2 code written into an MP4."""
    return _ISO639_2.get(code, code)


def _is_dropped_char(char: str) -> bool:
    """True for emoji, pictographs, and decorative marks."""
    code = ord(char)
    if code in {0x200B, 0x200C, 0x200D, 0xFE0E, 0xFE0F, 0x20E3, 0xFEFF}:
        return True
    if 0xFE00 <= code <= 0xFE0F or 0xE0000 <= code <= 0xE007F:
        return True
    if 0x1F000 <= code <= 0x1FAFF or 0x1F1E6 <= code <= 0x1F1FF:
        return True
    if 0x2300 <= code <= 0x23FF or 0x2600 <= code <= 0x27BF or 0x2B00 <= code <= 0x2BFF:
        return True
    category = unicodedata.category(char)
    return category in {"So", "Sk"} and code >= 0x2100


def _is_category(phrase: str) -> bool:
    words = _CATEGORY_WORDS.findall(phrase)
    if not words or len(words) > 4:
        return False
    lettered = [word for word in words if any(char.isalpha() for char in word)]
    if not lettered:
        return False
    if all(word.isupper() and len(word) >= 2 for word in lettered):
        return True
    lowered = [word.casefold() for word in words]
    if " ".join(lowered) in CATEGORIES:
        return True
    return all(word in CATEGORIES for word in lowered)


def _strip_categories(title: str) -> str:
    for _ in range(6):
        title = title.strip()
        wrapped = _LEADING_WRAPPER.match(title)
        if wrapped and _is_category(wrapped.group(1)) and wrapped.group(2).strip():
            title = wrapped.group(2).strip()
            continue
        labeled = _LEADING_LABEL.match(title)
        if labeled and _is_category(labeled.group(1)) and labeled.group(2).strip():
            title = labeled.group(2).strip()
            continue
        break
    return title


def _is_technical_token(token: str) -> bool:
    return token.strip().casefold() in TECHNICAL


def _strip_technical(title: str) -> str:
    title = _BRACKET_GROUP.sub(_replace_technical_bracket, title)
    if re.search(r"\s", title) is None and "." in title:
        parts = []
        for part in _DOTTED_PART.findall(title):
            token = part.strip()
            if token and not _is_technical_token(token):
                parts.append(token)
        return " ".join(parts)
    return _strip_standalone_technical(title)


def _replace_technical_bracket(match: re.Match[str]) -> str:
    tokens = _TOKEN.findall(match.group(1))
    if tokens and all(_is_technical_token(token) for token in tokens):
        return " "
    return match.group(0)


def _strip_standalone_technical(title: str) -> str:
    def replace(match: re.Match[str]) -> str:
        if _is_technical_token(match.group(0)):
            return " "
        return match.group(0)

    return _STANDALONE_TOKEN.sub(replace, title)


def _strip_trailing_video_id(title: str) -> str:
    match = _TRAILING_ID.search(title)
    if match is None:
        return title
    token = match.group("bracket") or match.group("bare")
    if not any(char.isdigit() for char in token):
        return title
    return title[:match.start()].rstrip()


def _finalize_title(title: str) -> str:
    kept = []
    for char in title:
        if char.isalnum() or char.isspace() or char in _TITLE_PUNCTUATION:
            kept.append(char)
        else:
            kept.append(" ")
    text = re.sub(r"\s+", " ", "".join(kept)).strip()
    return text.strip(" .-")


def _download_language(video_id: str, language: str, directory: Path, ytdlp: str) -> Path | None:
    directory.mkdir(parents=True, exist_ok=True)
    for automatic in (False, True):
        _run_yt_dlp(video_id, language, directory, ytdlp, automatic)
        found = sorted(directory.glob("*.srt"))
        if found:
            return found[0]
    return None


def _run_yt_dlp(video_id: str, language: str, directory: Path, ytdlp: str, automatic: bool) -> None:
    command = [
        ytdlp,
        "--ignore-config",
        "--no-progress",
        "--skip-download",
        "--no-playlist",
        "--convert-subs", "srt",
        "--sub-langs", f"{language}.*",
        "--write-auto-subs" if automatic else "--write-subs",
        "-o", str(directory / "%(id)s.%(language)s.%(ext)s"),
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    _run(command)


def build_partial_path(dest: Path) -> Path:
    return dest.with_name(dest.name + ".part")


def run_ffmpeg(command: list[str]) -> None:
    partial = Path(command[-1])
    result = _run(command)
    if result.returncode != 0:
        partial.unlink(missing_ok=True)
        detail = result.stderr.strip() or "ffmpeg failed"
        raise RuntimeError(detail)


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _require_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise SystemExit(
            f"Missing {name}. Install ffmpeg with:\n"
            "  brew install homebrew-ffmpeg/ffmpeg/ffmpeg --with-fdk-aac --with-libsoxr"
        )
    return path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remux YouTube videos into dated MP4 files with cleaned titles."
    )
    parser.add_argument(
        "directory",
        type=Path,
        help="Directory of video files. Subdirectories are not scanned.",
    )
    parser.add_argument(
        "--encode",
        action="store_true",
        help="Encode video as libx265 CRF 20 ultrafast (hvc1). Audio is copied.",
    )
    parser.add_argument(
        "--lang",
        default="en",
        help="Comma-separated subtitle locales, in track order. Regions are ignored in the output. Default: en.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if unidecode is None:
        sys.exit("Missing Python package unidecode. Install it with: pip install unidecode")
    _require_tool("ffmpeg")
    _require_tool("ffprobe")

    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        sys.exit("Set YOUTUBE_API_KEY to a YouTube Data API key.")

    directory = args.directory
    if not directory.is_dir():
        sys.exit(f"Not a directory: {directory}")

    languages = parse_languages(args.lang)
    paths = list_videos(directory)
    if not paths:
        print(f"No video files in {directory}.")
        return

    jobs: list[tuple[Path, str]] = []
    for path in paths:
        try:
            comment = read_comment(path)
        except RuntimeError as exc:
            print(f"Warning: {path.name}: {exc}", file=sys.stderr)
            continue
        video_id = extract_video_id(comment)
        if video_id is None:
            print(f"Warning: {path.name}: no YouTube URL in the comment tag, skipping.", file=sys.stderr)
            continue
        jobs.append((path, video_id))
    if not jobs:
        return

    published = fetch_published_dates([video_id for _path, video_id in jobs], api_key)
    ytdlp = shutil.which("yt-dlp")
    if languages and ytdlp is None:
        print(
            "Warning: yt-dlp is not installed; remuxing without subtitles. Install it with: brew install yt-dlp",
            file=sys.stderr,
        )

    failures = 0
    claimed: set[Path] = set()
    for path, video_id in jobs:
        moment = published.get(video_id)
        if moment is None:
            print(f"Warning: {path.name}: no publish date for {video_id}, skipping.", file=sys.stderr)
            continue
        title = strip_title(path.stem) or video_id
        dest = claim_destination(directory, local_calendar_date(moment), title, video_id, claimed)
        if dest is None:
            print(f"Warning: {path.name}: output already exists, skipping.", file=sys.stderr)
            continue
        print(f"Processing {path.name} ...")
        partial = build_partial_path(dest)
        try:
            with tempfile.TemporaryDirectory(prefix="youtube-remux-") as tmp:
                subtitles: list[tuple[Path, str]] = []
                if languages and ytdlp is not None:
                    subtitles = download_subtitles(video_id, languages, Path(tmp), ytdlp)
                command = build_ffmpeg_command(path, subtitles, partial, args.encode)
                run_ffmpeg(command)
            partial.replace(dest)
        except RuntimeError as exc:
            failures += 1
            partial.unlink(missing_ok=True)
            print(f"Error processing {path.name}: {exc}", file=sys.stderr)
            continue
        print(f"  -> {dest.name}")

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
