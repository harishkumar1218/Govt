import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings


def get_config_dir() -> Path:
    return getattr(settings, 'CONFIG_DIR', settings.BASE_DIR.parent / 'config')


@lru_cache(maxsize=32)
def load_json_config(name: str) -> dict | list:
    path = get_config_dir() / name
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def load_platform_config() -> dict:
    return load_json_config('platform.json')


def load_slug_registry() -> dict:
    return load_json_config('slug_registry.json')


def load_essay_prompts() -> dict:
    return load_json_config('essay_prompts.json')


def load_roadmap_templates() -> list:
    return load_json_config('roadmap_templates.json')


def load_exam_data_from_json() -> dict:
    """Load all exam track definitions from DB/exams/*.json (excluding pattern files)."""
    exams_dir = settings.BASE_DIR.parent / 'DB' / 'exams'
    data = {}
    for json_file in sorted(exams_dir.glob('*.json')):
        if '-pattern' in json_file.name:
            continue
        with open(json_file, encoding='utf-8') as f:
            exam = json.load(f)
        slug = exam.get('slug') or exam.get('_id')
        if slug:
            data[slug] = exam
    return data


def get_track_mapping(track_slug: str) -> dict | None:
    registry = load_slug_registry()
    return registry.get('tracks', {}).get(track_slug)


def get_rag_slug(track_slug: str) -> str:
    mapping = get_track_mapping(track_slug)
    return mapping['rag_slug'] if mapping else track_slug


def get_pattern_path(track_slug: str) -> Path | None:
    mapping = get_track_mapping(track_slug)
    if not mapping:
        return None
    return settings.BASE_DIR.parent / 'DB' / 'exams' / f"{mapping['pattern_slug']}-pattern.json"


def get_essay_prompts_for_track(track_slug: str) -> list[str]:
    prompts_config = load_essay_prompts()
    return prompts_config.get(track_slug) or prompts_config.get('default', [])


def get_quiz_schedule_for_weekday(weekday: int) -> str:
    platform = load_platform_config()
    topics = platform['quiz']['weekday_topics']
    return topics.get(str(weekday), topics.get('6', 'General Knowledge'))


def get_eligibility_categories() -> list[str]:
    return load_platform_config()['eligibility_categories']
