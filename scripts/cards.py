
#!/usr/bin/env python3

import html
import json
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROJECTS = ROOT / "assets" / "projects.json"
DEFAULT_OUTPUT = ROOT / "assets"

WIDTH = 440
HEIGHT = 124


def fetch_repository(full_name):
    url = f"https://api.github.com/repos/{full_name}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "kartik-profile-project-cards",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers)

    for attempt in range(3):
        try:
            with urlopen(request, timeout=20) as response:
                data = json.load(response)

            return {
                "description": data.get("description") or
                    "No description provided for this repository.",
                "language": data.get("language") or "Not specified",
                "stars": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "url": data.get("html_url") or
                    f"https://github.com/{full_name}",
            }

        except HTTPError as error:
            if error.code == 404:
                raise RuntimeError(
                    f"Repository not found or inaccessible: {full_name}"
                ) from error

            if error.code in (403, 429) and attempt < 2:
                time.sleep(2 ** (attempt + 1))
                continue

            raise RuntimeError(
                f"GitHub API returned HTTP {error.code} for {full_name}"
            ) from error

        except (URLError, TimeoutError) as error:
            if attempt < 2:
                time.sleep(2 ** (attempt + 1))
                continue

            raise RuntimeError(
                f"Could not fetch {full_name}: {error}"
            ) from error

    raise RuntimeError(f"Could not fetch repository: {full_name}")


def wrap_text(text, max_chars=56, max_lines=3):
    words = text.split()
    lines = []
    current = ""

    for word in words:
        candidate = f"{current} {word}".strip()

        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word

        if len(lines) == max_lines:
            break

    if current and len(lines) < max_lines:
        lines.append(current)

    consumed = " ".join(lines)
    if len(consumed) < len(text):
        if lines:
            lines[-1] = lines[-1][:max_chars - 3].rstrip() + "..."

    return lines or ["No description available."]


def make_svg(name, repository, info, theme):
    dark = theme == "dark"

    background = "#0d1117" if dark else "#ffffff"
    border = "#30363d" if dark else "#d0d7de"
    title_color = "#39d353" if dark else "#1a7f37"
    text_color = "#c9d1d9" if dark else "#24292f"
    muted = "#8b949e" if dark else "#57606a"
    language_color = {
        "JavaScript": "#f1e05a",
        "TypeScript": "#3178c6",
        "Python": "#3572A5",
        "Java": "#b07219",
        "C++": "#f34b7d",
        "C": "#555555",
        "HTML": "#e34c26",
        "CSS": "#663399",
    }.get(info["language"], "#8b949e")

    safe_name = html.escape(name)
    safe_repo = html.escape(repository)
    safe_description = [
        html.escape(line) for line in
        wrap_text(info["description"])
    ]
    safe_language = html.escape(info["language"])

    description_svg = "".join(
        f'<text x="16" y="{51 + i * 16}" '
        f'font-size="11" fill="{text_color}">{line}</text>'
        for i, line in enumerate(safe_description)
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg"
 width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
 <rect x="1" y="1" width="{WIDTH - 2}" height="{HEIGHT - 2}"
 rx="12" fill="{background}" stroke="{border}" stroke-width="1.5"/>
 <g font-family="Arial, Helvetica, sans-serif">
   <text x="16" y="26" font-size="13" font-weight="bold"
     fill="{title_color}">▣  {safe_name}</text>
   {description_svg}
   <circle cx="21" cy="98" r="4" fill="{language_color}"/>
   <text x="31" y="102" font-size="10" fill="{muted}">{safe_language}</text>
   <text x="158" y="102" font-size="10" fill="{muted}">★  {info["stars"]}</text>
   <text x="222" y="102" font-size="10" fill="{muted}">⑂  {info["forks"]}</text>
   <text x="16" y="116" font-size="8" fill="{muted}">{safe_repo}</text>
 </g>
</svg>
"""


def main():
    projects_file = Path(
        sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROJECTS
    )
    output_dir = Path(
        sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT
    )

    with projects_file.open(encoding="utf-8") as file:
        config = json.load(file)

    projects = config.get("projects", [])
    if not projects:
        raise RuntimeError("No projects found in projects.json")

    output_dir.mkdir(parents=True, exist_ok=True)

    for project in projects:
        name = project["name"]
        repository = project["repository"]

        print(f"Fetching {repository} ...")
        info = fetch_repository(repository)

        for theme in ("dark", "light"):
            filename = output_dir / f"card-{name}-{theme}.svg"
            svg = make_svg(name, repository, info, theme)
            filename.write_text(svg, encoding="utf-8")
            print(f"Generated {filename.relative_to(ROOT)}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
