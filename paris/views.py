from datetime import datetime, time as dt_time
import hashlib

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.cache import patch_cache_control
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from paris.models import Competition, Equipe, Match, Option, PropositionParis, Vote, VoteOption
from paris.moteur import VERSION_MOTEUR
from paris.reglement import regler_match
from paris import sofascore as sofa
from paris.serializers import (
    AuthSerializer,
    CompetitionSerializer,
    MatchDetailSerializer,
    MatchListeSerializer,
    NIVEAUX_COMPOS,
    PropositionCreateSerializer,
    PropositionSerializer,
    ResultatSerializer,
    VoteSerializer,
)

MIN_ECHANTILLON = 20


class Pagination30(PageNumberPagination):
    page_size = 30
    page_size_query_param = 'page_size'
    max_page_size = 50


class CacheETagMixin:
    """Cache HTTP court pour GET anonymes. Pas d’ETag partagé si session auth
    (évite de servir mon_vote d’un user à un autre via proxy)."""
    cache_seconds = 300

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if hasattr(response, 'render') and callable(response.render):
            response.render()
        if request.method == 'GET' and 200 <= response.status_code < 300:
            response['Vary'] = 'Cookie'
            if getattr(request, 'user', None) and request.user.is_authenticated:
                patch_cache_control(response, private=True, max_age=0, no_store=True)
            else:
                patch_cache_control(response, max_age=self.cache_seconds, public=True)
                body = response.content
                if body:
                    response['ETag'] = '"' + hashlib.md5(body).hexdigest() + '"'
        return response


def _fenetre_jour(d):
    """Borne [début, fin] d’un jour civil dans le fuseau Django (Europe/Paris)."""
    tz = timezone.get_current_timezone()
    debut = timezone.make_aware(datetime.combine(d, dt_time.min), tz)
    fin = timezone.make_aware(datetime.combine(d, dt_time.max), tz)
    return debut, fin


def _matchs_qs():
    return (
        Match.objects
        .select_related('competition', 'domicile', 'exterieur')
        .prefetch_related(
            Prefetch(
                'analyse__options',
                queryset=Option.objects.filter(niveau__in=NIVEAUX_COMPOS).prefetch_related(
                    'votes_consensus',
                ),
            ),
        )
    )


def _filtrer_matchs(qs, params):
    code = params.get('competition')
    if code:
        qs = qs.filter(competition__code=code)
    statut = params.get('statut')
    if statut:
        vals = [s.strip() for s in statut.split(',') if s.strip()]
        if len(vals) == 1:
            qs = qs.filter(statut=vals[0])
        elif vals:
            qs = qs.filter(statut__in=vals)
    depuis = params.get('depuis')
    if depuis:
        d = parse_date(depuis)
        if d:
            debut, _ = _fenetre_jour(d)
            qs = qs.filter(coup_denvoi__gte=debut)
    jusqu_a = params.get('jusqu_a')
    if jusqu_a:
        d = parse_date(jusqu_a)
        if d:
            _, fin = _fenetre_jour(d)
            qs = qs.filter(coup_denvoi__lte=fin)
    return qs


class CompetitionList(CacheETagMixin, APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = Competition.objects.filter(actif=True)
        return Response(CompetitionSerializer(qs, many=True).data)


class MatchList(CacheETagMixin, APIView):
    permission_classes = [AllowAny]
    pagination_class = Pagination30

    def get(self, request):
        qs = _filtrer_matchs(_matchs_qs(), request.query_params)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        ser = MatchListeSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(ser.data)


class MatchDetail(CacheETagMixin, APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        match = get_object_or_404(
            Match.objects.select_related(
                'competition', 'domicile', 'exterieur', 'analyse', 'contexte',
            ).prefetch_related('analyse__options__votes_consensus'),
            pk=pk,
        )
        return Response(MatchDetailSerializer(match, context={'request': request}).data)


class MatchResultat(APIView):
    """Saisie de score réservée au staff (évite falsification anonyme des tips)."""
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        match = get_object_or_404(Match, pk=pk)
        ser = ResultatSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        match.buts_dom = data['buts_dom']
        match.buts_ext = data['buts_ext']
        match.buts_dom_mt = data.get('buts_dom_mt')
        match.buts_ext_mt = data.get('buts_ext_mt')
        match.statut = 'termine'
        match.save()
        regler_match(match)
        match = Match.objects.select_related(
            'competition', 'domicile', 'exterieur', 'analyse', 'contexte',
        ).prefetch_related('analyse__options__votes_consensus').get(pk=match.pk)
        return Response(MatchDetailSerializer(match, context={'request': request}).data)


def _bloc_stats(options):
    n = len(options)
    gagnes = sum(1 for o in options if o.resultat == 'gagne')
    attendu = sum(o.probabilite for o in options) / n if n else None
    return {
        'n': n,
        'gagnes': gagnes,
        'taux': None if n < MIN_ECHANTILLON else (gagnes / n if n else None),
        'attendu': attendu,
        'echantillon_trop_petit': n < MIN_ECHANTILLON,
    }


def _options_reglees(params):
    qs = (
        Option.objects
        .filter(resultat__in=('gagne', 'perdu'))
        .select_related(
            'analyse__match__competition',
            'analyse__match__domicile',
            'analyse__match__exterieur',
        )
    )
    code = params.get('competition')
    if code:
        qs = qs.filter(analyse__match__competition__code=code)
    depuis = params.get('depuis')
    if depuis:
        d = parse_date(depuis)
        if d:
            debut, _ = _fenetre_jour(d)
            qs = qs.filter(analyse__match__coup_denvoi__gte=debut)
    jusqu_a = params.get('jusqu_a')
    if jusqu_a:
        d = parse_date(jusqu_a)
        if d:
            _, fin = _fenetre_jour(d)
            qs = qs.filter(analyse__match__coup_denvoi__lte=fin)
    niveau = params.get('niveau')
    if niveau:
        qs = qs.filter(niveau=niveau)
    return qs


class Verification(CacheETagMixin, APIView):
    permission_classes = [AllowAny]
    cache_seconds = 60

    def get(self, request):
        options = list(_options_reglees(request.query_params).exclude(
            niveau='detail',
        ))
        par_niveau = {}
        for niv in NIVEAUX_COMPOS:
            par_niveau[niv] = _bloc_stats([o for o in options if o.niveau == niv])
        familles = sorted({o.famille for o in options})
        par_famille = {
            fam: _bloc_stats([o for o in options if o.famille == fam])
            for fam in familles
        }
        return Response({
            'par_niveau': par_niveau,
            'par_famille': par_famille,
            'total_reglees': len(options),
        })


class VerificationDetail(CacheETagMixin, APIView):
    permission_classes = [AllowAny]
    cache_seconds = 60

    def get(self, request):
        qs = _options_reglees(request.query_params)
        niveau = request.query_params.get('niveau')
        if niveau:
            qs = qs.filter(niveau=niveau)
        else:
            qs = qs.filter(niveau__in=NIVEAUX_COMPOS)
        qs = qs.order_by('-analyse__match__coup_denvoi', 'niveau')
        lignes = []
        for o in qs[:400]:
            m = o.analyse.match
            lignes.append({
                'match_id': m.id,
                'libelle_match': f'{m.domicile.nom_court} – {m.exterieur.nom_court}',
                'competition': m.competition.code,
                'coup_denvoi': m.coup_denvoi,
                'option': o.libelle,
                'code': o.code,
                'famille': o.famille,
                'niveau': o.niveau,
                'probabilite': o.probabilite,
                'resultat': o.resultat,
            })
        return Response({'results': lignes})


class Info(CacheETagMixin, APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        u = request.user
        return Response({
            'version_moteur': VERSION_MOTEUR,
            'authentifie': u.is_authenticated,
            'username': u.username if u.is_authenticated else None,
        })


class Register(APIView):
    permission_classes = [AllowAny]
    # Pas de SessionAuthentication ici : évite un 403 CSRF au premier login PWA.
    authentication_classes = []

    def post(self, request):
        ser = AuthSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        if User.objects.filter(username__iexact=data['username']).exists():
            return Response({'detail': 'Ce pseudo est déjà pris.'}, status=400)
        user = User(username=data['username'].strip(), email=data.get('email') or '')
        try:
            validate_password(data['password'], user=user)
        except DjangoValidationError as e:
            return Response({'detail': ' '.join(e.messages)}, status=400)
        user = User.objects.create_user(
            username=user.username,
            password=data['password'],
            email=data.get('email') or '',
        )
        login(request, user)
        return Response({'authentifie': True, 'username': user.username})


class Login(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        ser = AuthSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        # Login insensible à la casse du pseudo.
        existing = User.objects.filter(username__iexact=data['username'].strip()).first()
        user = authenticate(
            request,
            username=existing.username if existing else data['username'],
            password=data['password'],
        )
        if user is None:
            return Response({'detail': 'Identifiants incorrects.'}, status=400)
        login(request, user)
        return Response({'authentifie': True, 'username': user.username})


class Logout(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        logout(request)
        return Response({'authentifie': False})


def _propositions_qs(match):
    return (
        PropositionParis.objects
        .filter(match=match)
        .select_related('auteur')
        .annotate(
            likes=Count('votes', filter=Q(votes__choix='like')),
            dislikes=Count('votes', filter=Q(votes__choix='dislike')),
        )
    )


class PropositionListCreate(APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return [AllowAny()]

    def get(self, request, pk):
        match = get_object_or_404(Match, pk=pk)
        qs = _propositions_qs(match)
        return Response({
            'results': PropositionSerializer(
                qs, many=True, context={'request': request},
            ).data,
        })

    def post(self, request, pk):
        match = get_object_or_404(Match, pk=pk)
        ser = PropositionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        prop = PropositionParis.objects.create(
            match=match,
            auteur=request.user,
            libelle=ser.to_libelle(),
            confiance=ser.validated_data.get('confiance', 50),
        )
        prop = _propositions_qs(match).get(pk=prop.pk)
        return Response(
            PropositionSerializer(prop, context={'request': request}).data,
            status=201,
        )


class PropositionVote(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, prop_id):
        match = get_object_or_404(Match, pk=pk)
        prop = get_object_or_404(PropositionParis, pk=prop_id, match=match)
        ser = VoteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        Vote.objects.update_or_create(
            proposition=prop,
            user=request.user,
            defaults={'choix': ser.validated_data['choix']},
        )
        prop = _propositions_qs(match).get(pk=prop.pk)
        return Response(PropositionSerializer(prop, context={'request': request}).data)


class OptionVote(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, opt_id):
        match = get_object_or_404(Match, pk=pk)
        option = get_object_or_404(Option, pk=opt_id, analyse__match=match)
        ser = VoteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        VoteOption.objects.update_or_create(
            option=option,
            user=request.user,
            defaults={'choix': ser.validated_data['choix']},
        )
        option = Option.objects.prefetch_related('votes_consensus').get(pk=option.pk)
        from paris.serializers import OptionDetailSerializer
        return Response(OptionDetailSerializer(option, context={'request': request}).data)


def _sid_equipe(eq: Equipe) -> int | None:
    """SofaScore id connu, ou résolution via recherche (sans casser l’unicité)."""
    if eq.sofascore_id:
        return eq.sofascore_id
    found = sofa.chercher_equipe_id(eq.nom) or sofa.chercher_equipe_id(eq.nom_court)
    if not found:
        return None
    if not Equipe.objects.filter(sofascore_id=found).exclude(pk=eq.pk).exists():
        eq.sofascore_id = found
        eq.save(update_fields=['sofascore_id'])
    return found


class EquipeLogo(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        from django.core.cache import cache
        from django.http import HttpResponse

        eq = get_object_or_404(Equipe, pk=pk)
        sid = _sid_equipe(eq)

        if sid:
            key = f'logo:{sid}'
            cached = cache.get(key)
            if cached:
                body, ctype = cached
            else:
                try:
                    body, ctype = sofa.logo_bytes(sid)
                    cache.set(key, (body, ctype), 60 * 60 * 24)
                except sofa.SofaScoreErreur:
                    body = sofa.logo_svg_placeholder(eq.nom, eq.nom_court)
                    ctype = 'image/svg+xml'
                    cache.set(key + ':svg', (body, ctype), 60 * 60)
        else:
            body = sofa.logo_svg_placeholder(eq.nom, eq.nom_court)
            ctype = 'image/svg+xml'

        resp = HttpResponse(body, content_type=ctype)
        resp['Cache-Control'] = 'public, max-age=86400'
        return resp


class EquipeInfos(APIView):
    permission_classes = [AllowAny]
    cache_seconds = 600

    def get(self, request, pk):
        eq = get_object_or_404(Equipe, pk=pk)
        sid = _sid_equipe(eq)
        if not sid:
            return Response({'detail': 'Infos indisponibles pour cette équipe.'}, status=404)
        # compétition la plus récente liée
        tid = None
        m = (
            Match.objects.filter(Q(domicile=eq) | Q(exterieur=eq))
            .select_related('competition')
            .order_by('-coup_denvoi')
            .first()
        )
        if m and m.competition.sofascore_id:
            tid = m.competition.sofascore_id
        try:
            data = sofa.infos_equipe(sid, tournament_id=tid)
        except sofa.SofaScoreErreur as e:
            return Response({'detail': str(e)}, status=502)
        data['equipe_id'] = eq.id
        data['nom_court'] = eq.nom_court or data.get('nom_court')
        data['nom'] = eq.nom or data.get('nom')
        return Response(data)


@ensure_csrf_cookie
def app(request, *args, **kwargs):
    return render(request, 'app.html', {
        'version_moteur': VERSION_MOTEUR,
        'annee': datetime.now().year,
    })
