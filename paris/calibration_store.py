"""Chargement / sauvegarde des tables de calibration apprises."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from django.conf import settings

from paris.moteur import CALIBRATION_DEFAUT

CALIBRATION_FILE = Path(settings.BASE_DIR) / 'data' / 'calibration.json'


def chemin_calibration() -> Path:
    return CALIBRATION_FILE


def charger_tables() -> dict[str, list[tuple[float, float]]]:
    """Tables actives = défaut fusionné avec le fichier appris (si présent)."""
    tables = deepcopy(CALIBRATION_DEFAUT)
    path = chemin_calibration()
    if not path.is_file():
        return tables
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return tables
    learned = raw.get('tables') or {}
    for fam, points in learned.items():
        if not isinstance(points, list) or len(points) < 2:
            continue
        try:
            tables[fam] = [(float(a), float(b)) for a, b in points]
        except (TypeError, ValueError):
            continue
    return tables


def meta_calibration() -> dict[str, Any]:
    path = chemin_calibration()
    if not path.is_file():
        return {'version': 0, 'existe': False}
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {'version': 0, 'existe': False}
    return {
        'existe': True,
        'version': int(raw.get('version') or 0),
        'updated_at': raw.get('updated_at'),
        'echantillons': raw.get('echantillons') or {},
    }


def sauver_tables(
    tables: dict[str, list[tuple[float, float]]],
    *,
    echantillons: dict[str, int] | None = None,
    version: int | None = None,
) -> Path:
    path = chemin_calibration()
    path.parent.mkdir(parents=True, exist_ok=True)
    prev = meta_calibration()
    ver = version if version is not None else int(prev.get('version') or 0) + 1
    from django.utils import timezone

    payload = {
        'version': ver,
        'updated_at': timezone.now().isoformat(),
        'echantillons': echantillons or {},
        'tables': {
            fam: [[round(a, 4), round(b, 4)] for a, b in pts]
            for fam, pts in tables.items()
        },
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    # Invalide le cache processus.
    try:
        from paris import moteur
        moteur.invalider_calibration_cache()
    except Exception:  # noqa: BLE001
        pass
    return path
