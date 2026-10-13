
import json
import math
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

USERNAME = "kartik-kumar-pandey"
TOKEN = os.environ.get("GITHUB_TOKEN", "")

DEFAULT_SKILLS = {
    "labels": [
        "Frontend",
        "Backend",
        "Databases",
        "Cloud",
        "Languages",
        "Problem Solving"
    ],
    "values": [70, 65, 60, 40, 65, 60]
}

skills_path = ASSETS / "skills.json"

if skills_path.exists():
    skills = json.loads(skills_path.read_text(encoding="utf-8"))
else:
    skills = DEFAULT_SKILLS
    skills_path.write_text(
        json.dumps(skills, indent=2) + "\n",
        encoding="utf-8"
    )

def get_languages():
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Kartik-Profile-Radar"
    }

    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    request = urllib.request.Request(
        f"https://api.github.com/users/{USERNAME}/repos?per_page=100&type=owner",
        headers=headers
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        repositories = json.load(response)

    totals = {}

    for repo in repositories:
        if repo.get("fork"):
            continue

        url = repo.get("languages_url")
        if not url:
            continue

        request = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                languages = json.load(response)
        except Exception as error:
            print(f"Skipping {repo.get('name')}: {error}")
            continue

        for language, count in languages.items():
            totals[language] = totals.get(language, 0) + count

    if not totals:
        raise RuntimeError(
            "GitHub returned no language data. Check repository visibility "
            "and API access."
        )

    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    ranked = ranked[:6]

    labels = [name for name, _ in ranked]
    values = [count for _, count in ranked]
    maximum = max(values)

    normalized = [round(value / maximum * 100) for value in values]
    return labels, normalized

def make_radar(title, labels, values, dark):
    width, height = 440, 380
    cx, cy, radius = 220, 185, 115

    background = "#0d1117" if dark else "#ffffff"
    foreground = "#c9d1d9" if dark else "#24292f"
    grid = "#30363d" if dark else "#d0d7de"
    accent = "#58a6ff"
    fill = "#1f6feb"

    def position(index, scale):
        angle = -math.pi / 2 + 2 * math.pi * index / len(labels)
        return (
            cx + radius * scale * math.cos(angle),
            cy + radius * scale * math.sin(angle)
        )

    output = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        f'<rect width="100%" height="100%" rx="12" fill="{background}"/>',
        f'<text x="{cx}" y="28" text-anchor="middle" '
        f'font-family="Arial,sans-serif" font-size="16" '
        f'font-weight="bold" fill="{foreground}">{title}</text>'
    ]

    for level in (0.25, 0.5, 0.75, 1.0):
        points = [position(i, level) for i in range(len(labels))]
        coordinates = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        output.append(
            f'<polygon points="{coordinates}" fill="none" '
            f'stroke="{grid}" stroke-width="1"/>'
        )

    for i, label in enumerate(labels):
        x, y = position(i, 1)
        output.append(
            f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" '
            f'stroke="{grid}"/>'
        )

        lx, ly = position(i, 1.23)
        anchor = "middle"
        if math.cos(-math.pi / 2 + 2 * math.pi * i / len(labels)) > 0.25:
            anchor = "start"
        elif math.cos(-math.pi / 2 + 2 * math.pi * i / len(labels)) < -0.25:
            anchor = "end"

        safe_label = (
            label.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;")
                 .replace('"', "&quot;")
        )

        output.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" '
            f'font-family="Arial,sans-serif" font-size="11" '
            f'fill="{foreground}">{safe_label}</text>'
        )

    points = [
        position(i, max(0, min(100, value)) / 100)
        for i, value in enumerate(values)
    ]

    coordinates = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    output.append(
        f'<polygon points="{coordinates}" fill="{fill}" '
        f'fill-opacity="0.35" stroke="{accent}" stroke-width="2.5"/>'
    )

    for x, y in points:
        output.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{accent}"/>'
        )

    output.append("</svg>")
    return "\n".join(output) + "\n"

def save_pair(prefix, title, labels, values):
    for theme, dark in (("dark", True), ("light", False)):
        filename = ASSETS / f"{prefix}-{theme}.svg"
        filename.write_text(
            make_radar(title, labels, values, dark),
            encoding="utf-8"
        )
        print(f"Generated {filename.relative_to(ROOT)}")

skill_labels = skills["labels"]
skill_values = skills["values"]

if len(skill_labels) != len(skill_values):
    raise ValueError("Skill labels and values must have the same length.")

if not skill_labels or any(not 0 <= value <= 100 for value in skill_values):
    raise ValueError("Provide skill values between 0 and 100.")

save_pair(
    "radar",
    "Self-Rated Skills",
    skill_labels,
    skill_values
)

language_labels, language_values = get_languages()

save_pair(
    "radar-langs",
    "Repository Languages",
    language_labels,
    language_values
)

print("All four radar charts generated successfully.")
