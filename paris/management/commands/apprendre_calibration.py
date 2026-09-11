"""Apprentissage des courbes marché (v3.1) à partir des tips réglés."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy

import numpy as np
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date

from paris.calibrage import (
    CALIBRATION_MARCHE_DEFAUT,
    COMPLEMENT,
    cle_marche_depuis_code,
)
from paris.calibration_store import charger_tables, sauver_tables
from paris.models import Option
from paris.views import _fenetre_jour

NIVEAUX_APPRIS = ('prudente', 'filet', 'equilibree', 'audacieuse')
MIN_MARCHE = 12
MIN_FAMILLE = MIN_MARCHE  # alias rétrocompat tests / CLI
MIN_BIN = 4
BINS = (
    (0.20, 0.40),
    (0.40, 0.55),
    (0.55, 0.70),
    (0.70, 0.82),
    (0.82, 0.95),
)
POIDS_PRIOR = 18.0


def _monotone(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    pts = sorted(points, key=lambda t: t[0])
    out = []
    last_y = 0.0
    for x, y in pts:
        y = max(float(y), last_y)
        y = float(np.clip(y, 0.01, 0.99))
        out.append((float(x), y))
        last_y = y
    return out


def _cle_directe(marche) -> str | None:
    if marche is None:
        return None
    if isinstance(marche, tuple) and marche and marche[0] == COMPLEMENT:
        return None  # on n’apprend que la direction directe
    if isinstance(marche, str) and marche in CALIBRATION_MARCHE_DEFAUT:
        return marche
    return None


def apprendre_depuis_options(options, min_famille: int = MIN_MARCHE) -> tuple[dict, dict[str, int]]:
    """Retourne (tables marché, echantillons_par_clé).

    min_famille conserve le nom historique (= min observations par marché).
    """
    by_m: dict[str, list[tuple[float, int]]] = defaultdict(list)
    for o in options:
        code = getattr(o, 'code', None)
        marche = cle_marche_depuis_code(code)
        cle = _cle_directe(marche)
        if not cle:
            continue
        if getattr(o, 'origine', 'calcul') == 'marche':
            continue
        by_m[cle].append((float(o.probabilite), 1 if o.resultat == 'gagne' else 0))

    base = charger_tables()
    learned = deepcopy(base)
    echantillons: dict[str, int] = {}

    for cle, rows in by_m.items():
        n = len(rows)
        echantillons[cle] = n
        if n < min_famille:
            continue
        empiriques: list[tuple[float, float, int]] = []
        for lo, hi in BINS:
            bucket = [(p, y) for p, y in rows if lo <= p < hi]
            if len(bucket) < MIN_BIN:
                continue
            mx = sum(p for p, _ in bucket) / len(bucket)
            my = sum(y for _, y in bucket) / len(bucket)
            empiriques.append((mx, my, len(bucket)))

        if not empiriques:
            continue

        prior = CALIBRATION_MARCHE_DEFAUT.get(cle) or base.get(cle) or []
        merged: list[tuple[float, float]] = list(prior)
        for mx, my, nb in empiriques:
            xs = [a for a, _ in prior] or [mx]
            ys = [b for _, b in prior] or [my]
            y0 = float(np.interp(mx, xs, ys))
            w = nb / (nb + POIDS_PRIOR)
            yb = (1 - w) * y0 + w * my
            merged.append((mx, yb))

        learned[cle] = _monotone(merged)

    return learned, echantillons


class Command(BaseCommand):
    help = (
        'Affine les courbes marché (data/calibration.json, schéma marche_v31) '
        'à partir des tips déjà réglés.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--depuis', default='', help='AAAA-MM-JJ')
        parser.add_argument('--jusqu_a', default='', help='AAAA-MM-JJ')
        parser.add_argument(
            '--min-famille', type=int, default=MIN_MARCHE,
            help='Minimum d’observations par marché pour mettre à jour',
        )

    def handle(self, *args, **opts):
        min_famille = opts['min_famille']

        qs = (
            Option.objects
            .filter(
                resultat__in=('gagne', 'perdu'),
                niveau__in=NIVEAUX_APPRIS,
            )
            .select_related('analyse__match')
        )
        if opts['depuis']:
            d = parse_date(opts['depuis'])
            if d:
                debut, _ = _fenetre_jour(d)
                qs = qs.filter(analyse__match__coup_denvoi__gte=debut)
        if opts['jusqu_a']:
            d = parse_date(opts['jusqu_a'])
            if d:
                _, fin = _fenetre_jour(d)
                qs = qs.filter(analyse__match__coup_denvoi__lte=fin)

        options = list(qs)
        if not options:
            self.stdout.write(self.style.WARNING('Aucun tip réglé : rien à apprendre.'))
            return

        tables, echantillons = apprendre_depuis_options(options, min_famille=min_famille)
        maj = [f for f, n in echantillons.items() if n >= min_famille]
        self.stdout.write(
            f'{len(options)} tips analysés. Marchés mis à jour : '
            + (', '.join(maj) if maj else '(aucun, échantillon insuffisant)')
        )
        for cle, n in sorted(echantillons.items()):
            self.stdout.write(f'  · {cle}: {n} obs.')

        if opts['dry_run']:
            self.stdout.write(self.style.WARNING('Dry-run : fichier non écrit.'))
            return

        # N’écrit que les overrides (clés touchées + base fusionnée ok).
        path = sauver_tables(tables, echantillons=echantillons)
        self.stdout.write(self.style.SUCCESS(f'Calibration enregistrée → {path}'))
