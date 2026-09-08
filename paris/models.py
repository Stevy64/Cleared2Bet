from django.conf import settings
from django.db import models


class Competition(models.Model):
    code = models.SlugField(max_length=20, unique=True)   # 'PL', 'LIGA', 'UCL'
    nom = models.CharField(max_length=80)                  # 'Premier League'
    pays = models.CharField(max_length=40, blank=True)
    ordre = models.PositiveSmallIntegerField(default=100)  # ordre d'affichage
    actif = models.BooleanField(default=True)
    sofascore_id = models.PositiveIntegerField(null=True, blank=True, unique=True)

    class Meta:
        ordering = ['ordre', 'nom']

    def __str__(self):
        return self.nom


class Equipe(models.Model):
    nom = models.CharField(max_length=80, unique=True)
    nom_court = models.CharField(max_length=24)            # pour l'affichage mobile
    slug = models.SlugField(unique=True)
    sofascore_id = models.PositiveIntegerField(null=True, blank=True, unique=True)

    def __str__(self):
        return self.nom_court or self.nom


class Match(models.Model):
    STATUT = [('a_venir', 'À venir'), ('en_cours', 'En cours'),
              ('termine', 'Terminé'), ('reporte', 'Reporté')]

    competition = models.ForeignKey(Competition, on_delete=models.PROTECT,
                                    related_name='matchs')
    domicile = models.ForeignKey(Equipe, on_delete=models.PROTECT, related_name='+')
    exterieur = models.ForeignKey(Equipe, on_delete=models.PROTECT, related_name='+')
    coup_denvoi = models.DateTimeField(db_index=True)
    journee = models.CharField(max_length=40, blank=True)  # 'Journée 1'
    statut = models.CharField(max_length=10, choices=STATUT, default='a_venir')
    sofascore_id = models.PositiveIntegerField(null=True, blank=True, unique=True)

    # résultat, rempli après le match
    buts_dom = models.PositiveSmallIntegerField(null=True, blank=True)
    buts_ext = models.PositiveSmallIntegerField(null=True, blank=True)
    buts_dom_mt = models.PositiveSmallIntegerField(null=True, blank=True)
    buts_ext_mt = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['coup_denvoi']
        indexes = [models.Index(fields=['statut', 'coup_denvoi']),
                   models.Index(fields=['competition', 'coup_denvoi'])]
        constraints = [models.UniqueConstraint(
            fields=['domicile', 'exterieur', 'coup_denvoi'], name='match_unique')]

    def __str__(self):
        return f"{self.domicile} – {self.exterieur}"

    @property
    def score(self):
        if self.buts_dom is None: return None
        return f"{self.buts_dom}-{self.buts_ext}"


class Cote(models.Model):
    """Une cote relevée. Sert d'entrée au calcul, jamais de critère de décision."""
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='cotes')
    bookmaker = models.CharField(max_length=40)            # 'consensus', 'PMUG', ...
    marche = models.CharField(max_length=20)               # '1X2', 'OU25', 'BTTS'
    selection = models.CharField(max_length=20)            # '1', 'N', '2', 'over', 'under'
    valeur = models.DecimalField(max_digits=7, decimal_places=3)
    nb_sources = models.PositiveSmallIntegerField(default=1)
    releve_le = models.DateTimeField()

    class Meta:
        indexes = [models.Index(fields=['match', 'marche'])]

    def __str__(self):
        return f"{self.match} {self.marche} {self.selection} {self.valeur}"


class Analyse(models.Model):
    """Le résultat du moteur pour un match, à un instant donné."""
    match = models.OneToOneField(Match, on_delete=models.CASCADE, related_name='analyse')
    buts_dom_attendus = models.FloatField()
    buts_ext_attendus = models.FloatField()
    p1 = models.FloatField()
    pn = models.FloatField()
    p2 = models.FloatField()
    score_probable = models.CharField(max_length=8)
    profil = models.CharField(max_length=16)               # equilibre / moyen / desequilibre
    marge_marche = models.FloatField()
    residu = models.FloatField()                           # qualité de l'ajustement
    version_moteur = models.CharField(max_length=12)
    calcule_le = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Analyse {self.match}"


class Option(models.Model):
    """Une option de pari proposée pour un match."""
    NIVEAU = [('prudente', 'Prudente'), ('equilibree', 'Équilibrée'),
              ('audacieuse', 'Audacieuse'), ('filet', 'Filet de sécurité'),
              ('detail', 'Détail')]
    ORIGINE = [('marche', 'Marché'), ('calcul', 'Calculé')]
    RESULTAT = [('attente', 'En attente'), ('gagne', 'Gagné'),
                ('perdu', 'Perdu'), ('annule', 'Annulé')]

    analyse = models.ForeignKey(Analyse, on_delete=models.CASCADE, related_name='options')
    famille = models.CharField(max_length=32)              # 'Total buts', 'Handicap', ...
    code = models.CharField(max_length=32)                 # CLÉ : voir évaluateur ci-dessous
    libelle = models.CharField(max_length=120)             # texte affiché, en français
    probabilite = models.FloatField()                      # après correction
    cote_juste = models.FloatField()
    niveau = models.CharField(max_length=12, choices=NIVEAU, default='detail')
    origine = models.CharField(max_length=8, choices=ORIGINE)

    # rempli automatiquement après le match
    resultat = models.CharField(max_length=8, choices=RESULTAT, default='attente')
    regle_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['niveau', 'resultat']),
                   models.Index(fields=['famille', 'resultat'])]

    def __str__(self):
        return f"{self.libelle} ({self.code})"


class Contexte(models.Model):
    """Forme, absents, à savoir. Texte libre en français, affiché tel quel."""
    match = models.OneToOneField(Match, on_delete=models.CASCADE, related_name='contexte')
    forme_dom = models.TextField(blank=True)
    forme_ext = models.TextField(blank=True)
    absents_dom = models.TextField(blank=True)
    absents_ext = models.TextField(blank=True)
    tendance_buts = models.TextField(blank=True)
    a_savoir = models.TextField(blank=True)
    confrontations = models.TextField(blank=True)
    fiabilite = models.CharField(max_length=8, default='moyenne')
    source = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"Contexte {self.match}"


class PropositionParis(models.Model):
    """Proposition libre d'un utilisateur sur un match (pour stats / votes)."""
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='propositions')
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='propositions',
    )
    libelle = models.CharField(max_length=160)
    confiance = models.PositiveSmallIntegerField(default=50)  # 1–99 affiché en %
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.libelle} ({self.match})"

    @property
    def likes(self):
        return self.votes.filter(choix='like').count()

    @property
    def dislikes(self):
        return self.votes.filter(choix='dislike').count()


class Vote(models.Model):
    CHOIX = [('like', 'Like'), ('dislike', 'Dislike')]
    proposition = models.ForeignKey(
        PropositionParis, on_delete=models.CASCADE, related_name='votes',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='votes',
    )
    choix = models.CharField(max_length=8, choices=CHOIX)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['proposition', 'user'], name='vote_unique_user_prop',
            ),
        ]

    def __str__(self):
        return f"{self.user} → {self.choix}"


class VoteOption(models.Model):
    """Accord / désaccord sur une recommandation du moteur (consensus)."""
    CHOIX = [('like', 'D’accord'), ('dislike', 'Pas d’accord')]
    option = models.ForeignKey(
        Option, on_delete=models.CASCADE, related_name='votes_consensus',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='votes_options',
    )
    choix = models.CharField(max_length=8, choices=CHOIX)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['option', 'user'], name='vote_unique_user_option',
            ),
        ]

    def __str__(self):
        return f"{self.user} → {self.option_id} {self.choix}"
