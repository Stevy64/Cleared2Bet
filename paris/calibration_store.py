"""Chargement / sauvegarde des overrides de calibration (clés de marché v3.1)."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from django.conf import settings

from paris.calibrage import CALIBRATION_MARCHE_DEFAUT

CALIBRATION_FILE = Path(settings.BASE_DIR) / 'data' / 'calibration.json'


def chemin_calibration() -> Path:
    return CALIBRATION_FILE


def charger_overrides_marche() -> dict[str, list[tuple[float, float]]]:
    """Overrides appris uniquement (clés de marché, pas familles)."""
    path = chemin_calibration()
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}
    learned = raw.get('tables') or {}
    out: dict[str, list[tuple[float, float]]] = {}
    for cle, points in learned.items():
        if not isinstance(points, list) or len(points) < 2:
            continue
        # Ignore l’ancien format v3.0 (familles) : seules les clés présentes
        # dans le JSON marché sont acceptées.
        if cle not in CALIBRATION_MARCHE_DEFAUT and not cle.startswith(('+', 'MT', 'HC', 'BTTS', 'dom', 'ext')):
            if cle in (
                'Total buts', 'Mi-temps', 'Handicap', 'BTTS',
                'Une équipe marque', "Une equipe marque",
            ):
                continue
        try:
            out[cle] = [(float(a), float(b)) for a, b in points]
        except (TypeError, ValueError):
            continue
    return out


def charger_tables() -> dict[str, list[tuple[float, float]]]:
    """Tables actives = défaut marché + overrides (compat API historique)."""
    tables = deepcopy(CALIBRATION_MARCHE_DEFAUT)
    tables.update(charger_overrides_marche())
    return tables


def meta_calibration() -> dict[str, Any]:
    path = chemin_calibration()
    if not path.is_file():
        return {'version': 0, 'existe': False, 'schema': 'marche_v31'}
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {'version': 0, 'existe': False, 'schema': 'marche_v31'}
    return {
        'existe': True,
        'version': int(raw.get('version') or 0),
        'updated_at': raw.get('updated_at'),
        'echantillons': raw.get('echantillons') or {},
        'schema': raw.get('schema') or 'marche_v31',
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
        'schema': 'marche_v31',
        'updated_at': timezone.now().isoformat(),
        'echantillons': echantillons or {},
        'tables': {
            cle: [[round(a, 4), round(b, 4)] for a, b in pts]
            for cle, pts in tables.items()
        },
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    try:
        from paris import calibrage, moteur
        calibrage.invalider_cache()
        moteur.invalider_calibration_cache()
    except Exception:  # noqa: BLE001
        pass
    return path
