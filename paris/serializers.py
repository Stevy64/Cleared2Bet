from rest_framework import serializers

from paris.models import (
    Analyse, Competition, Contexte, Match, Option, PropositionParis,
)
from paris.moteur import RESIDU_DOUTEUX

NIVEAUX_LISTE = ('prudente', 'equilibree', 'audacieuse')
# Compos du jour / historique : tips + filet de sécurité
NIVEAUX_COMPOS = ('prudente', 'equilibree', 'audacieuse', 'filet')


def _consensus(option, request):
    cached = getattr(option, '_consensus_cache', None)
    if cached is not None:
        return cached
    votes = list(option.votes_consensus.all())
    likes = sum(1 for v in votes if v.choix == 'like')
    dislikes = sum(1 for v in votes if v.choix == 'dislike')
    mon = None
    if request and getattr(request, 'user', None) and request.user.is_authenticated:
        uid = request.user.id
        for v in votes:
            if v.user_id == uid:
                mon = v.choix
                break
    total = likes + dislikes
    result = {
        'likes': likes,
        'dislikes': dislikes,
        'pct_likes': round(100 * likes / total) if total else None,
        'mon_vote': mon,
    }
    option._consensus_cache = result
    return result


class CompetitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competition
        fields = ('id', 'code', 'nom', 'pays', 'ordre')


class EquipeCourtSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nom = serializers.CharField()
    nom_court = serializers.CharField()
    slug = serializers.CharField()
    sofascore_id = serializers.IntegerField(allow_null=True)


class OptionListeSerializer(serializers.ModelSerializer):
    likes = serializers.SerializerMethodField()
    dislikes = serializers.SerializerMethodField()
    pct_likes = serializers.SerializerMethodField()
    mon_vote = serializers.SerializerMethodField()

    class Meta:
        model = Option
        fields = (
            'id', 'niveau', 'libelle', 'probabilite', 'resultat',
            'likes', 'dislikes', 'pct_likes', 'mon_vote',
        )

    def _c(self, obj):
        return _consensus(obj, self.context.get('request'))

    def get_likes(self, obj):
        return self._c(obj)['likes']

    def get_dislikes(self, obj):
        return self._c(obj)['dislikes']

    def get_pct_likes(self, obj):
        return self._c(obj)['pct_likes']

    def get_mon_vote(self, obj):
        return self._c(obj)['mon_vote']


class MatchListeSerializer(serializers.ModelSerializer):
    competition = CompetitionSerializer()
    domicile = EquipeCourtSerializer()
    exterieur = EquipeCourtSerializer()
    score = serializers.CharField(allow_null=True)
    options = serializers.SerializerMethodField()

    class Meta:
        model = Match
        fields = (
            'id', 'competition', 'domicile', 'exterieur',
            'coup_denvoi', 'journee', 'statut', 'score', 'options',
        )

    def get_options(self, obj):
        try:
            opts = [o for o in obj.analyse.options.all() if o.niveau in NIVEAUX_COMPOS]
        except Analyse.DoesNotExist:
            return []
        ordre = {n: i for i, n in enumerate(NIVEAUX_COMPOS)}
        opts.sort(key=lambda o: ordre.get(o.niveau, 9))
        return OptionListeSerializer(opts, many=True, context=self.context).data


class OptionDetailSerializer(serializers.ModelSerializer):
    likes = serializers.SerializerMethodField()
    dislikes = serializers.SerializerMethodField()
    pct_likes = serializers.SerializerMethodField()
    mon_vote = serializers.SerializerMethodField()

    class Meta:
        model = Option
        fields = (
            'id', 'famille', 'code', 'libelle', 'probabilite',
            'cote_juste', 'niveau', 'origine', 'resultat',
            'likes', 'dislikes', 'pct_likes', 'mon_vote',
        )

    def _c(self, obj):
        return _consensus(obj, self.context.get('request'))

    def get_likes(self, obj):
        return self._c(obj)['likes']

    def get_dislikes(self, obj):
        return self._c(obj)['dislikes']

    def get_pct_likes(self, obj):
        return self._c(obj)['pct_likes']

    def get_mon_vote(self, obj):
        return self._c(obj)['mon_vote']


class AnalyseSerializer(serializers.ModelSerializer):
    douteuse = serializers.SerializerMethodField()
    options = OptionDetailSerializer(many=True)

    class Meta:
        model = Analyse
        fields = (
            'buts_dom_attendus', 'buts_ext_attendus',
            'p1', 'pn', 'p2', 'score_probable', 'profil',
            'marge_marche', 'residu', 'douteuse',
            'version_moteur', 'calcule_le', 'options',
        )

    def get_douteuse(self, obj):
        return obj.residu > RESIDU_DOUTEUX


class ContexteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contexte
        fields = (
            'forme_dom', 'forme_ext', 'absents_dom', 'absents_ext',
            'tendance_buts', 'a_savoir', 'confrontations',
            'fiabilite', 'source',
        )


class MatchDetailSerializer(serializers.ModelSerializer):
    competition = CompetitionSerializer()
    domicile = EquipeCourtSerializer()
    exterieur = EquipeCourtSerializer()
    score = serializers.CharField(allow_null=True)
    analyse = serializers.SerializerMethodField()
    contexte = serializers.SerializerMethodField()

    class Meta:
        model = Match
        fields = (
            'id', 'competition', 'domicile', 'exterieur',
            'coup_denvoi', 'journee', 'statut',
            'buts_dom', 'buts_ext', 'buts_dom_mt', 'buts_ext_mt',
            'score', 'analyse', 'contexte',
        )

    def get_analyse(self, obj):
        try:
            return AnalyseSerializer(obj.analyse, context=self.context).data
        except Analyse.DoesNotExist:
            return None

    def get_contexte(self, obj):
        try:
            return ContexteSerializer(obj.contexte).data
        except Contexte.DoesNotExist:
            return None


class ResultatSerializer(serializers.Serializer):
    buts_dom = serializers.IntegerField(min_value=0, max_value=30)
    buts_ext = serializers.IntegerField(min_value=0, max_value=30)
    buts_dom_mt = serializers.IntegerField(
        min_value=0, max_value=30, required=False, allow_null=True,
    )
    buts_ext_mt = serializers.IntegerField(
        min_value=0, max_value=30, required=False, allow_null=True,
    )

    def validate(self, data):
        bd_mt, be_mt = data.get('buts_dom_mt'), data.get('buts_ext_mt')
        if (bd_mt is None) ^ (be_mt is None):
            raise serializers.ValidationError(
                'Les deux scores mi-temps doivent être fournis ensemble.'
            )
        if bd_mt is not None and be_mt is not None:
            if bd_mt > data['buts_dom'] or be_mt > data['buts_ext']:
                raise serializers.ValidationError(
                    'Le score mi-temps ne peut pas dépasser le score final.'
                )
        return data


class AuthSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, min_length=3)
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField(required=False, allow_blank=True)

class PropositionSerializer(serializers.ModelSerializer):
    auteur = serializers.CharField(source='auteur.username', read_only=True)
    likes = serializers.IntegerField(read_only=True)
    dislikes = serializers.IntegerField(read_only=True)
    mon_vote = serializers.SerializerMethodField()
    pct_likes = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()

    class Meta:
        model = PropositionParis
        fields = (
            'id', 'libelle', 'type', 'confiance', 'auteur', 'created_at',
            'likes', 'dislikes', 'pct_likes', 'mon_vote',
        )
        read_only_fields = ('id', 'auteur', 'created_at')

    def get_type(self, obj):
        for code, label in TYPES_PROPOSITION.items():
            if obj.libelle == label:
                return code
        return None

    def get_mon_vote(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        v = obj.votes.filter(user=request.user).first()
        return v.choix if v else None

    def get_pct_likes(self, obj):
        total = obj.likes + obj.dislikes
        if total == 0:
            return None
        return round(100 * obj.likes / total)


TYPES_PROPOSITION = {
    'vainqueur_dom': 'Vainqueur domicile',
    'nul': 'Match nul',
    'vainqueur_ext': 'Vainqueur extérieur',
    'plus_25': 'Plus de 2,5 buts',
    'moins_25': 'Moins de 2,5 buts',
}


class PropositionCreateSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=list(TYPES_PROPOSITION.keys()))
    confiance = serializers.IntegerField(min_value=1, max_value=99, default=50)

    def to_libelle(self):
        return TYPES_PROPOSITION[self.validated_data['type']]


class VoteSerializer(serializers.Serializer):
    choix = serializers.ChoiceField(choices=['like', 'dislike'])
