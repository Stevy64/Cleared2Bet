from django.contrib import admin

from .models import (
    Analyse, Competition, Contexte, Cote, Equipe, Match, Option,
    PropositionParis, Vote, VoteOption,
)


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ('code', 'nom', 'pays', 'ordre', 'actif')
    list_filter = ('actif',)
    search_fields = ('code', 'nom')
    ordering = ('ordre', 'nom')


@admin.register(Equipe)
class EquipeAdmin(admin.ModelAdmin):
    list_display = ('nom', 'nom_court', 'slug', 'sofascore_id')
    search_fields = ('nom', 'nom_court', 'slug')
    prepopulated_fields = {'slug': ('nom',)}


class CoteInline(admin.TabularInline):
    model = Cote
    extra = 0


class ContexteInline(admin.StackedInline):
    model = Contexte
    extra = 0
    max_num = 1


class OptionInline(admin.TabularInline):
    model = Option
    extra = 0
    readonly_fields = ('resultat', 'regle_le')


class AnalyseInline(admin.StackedInline):
    model = Analyse
    extra = 0
    max_num = 1


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = (
        'coup_denvoi', 'competition', 'domicile', 'exterieur',
        'statut', 'score',
    )
    list_filter = ('statut', 'competition')
    search_fields = ('domicile__nom', 'exterieur__nom', 'journee')
    date_hierarchy = 'coup_denvoi'
    autocomplete_fields = ('competition', 'domicile', 'exterieur')
    inlines = (ContexteInline, CoteInline, AnalyseInline)
    fieldsets = (
        (None, {
            'fields': (
                'competition', 'domicile', 'exterieur',
                'coup_denvoi', 'journee', 'statut',
            ),
        }),
        ('Résultat', {
            'fields': (
                'buts_dom', 'buts_ext', 'buts_dom_mt', 'buts_ext_mt',
            ),
            'description': (
                'Saisie manuelle du score. Le règlement des options '
                'se fera à l’étape 3 (commande regler_options).'
            ),
        }),
    )


@admin.register(Analyse)
class AnalyseAdmin(admin.ModelAdmin):
    list_display = (
        'match', 'profil', 'score_probable', 'residu',
        'version_moteur', 'calcule_le',
    )
    list_filter = ('profil', 'version_moteur')
    search_fields = (
        'match__domicile__nom', 'match__exterieur__nom',
    )
    inlines = (OptionInline,)
    readonly_fields = ('calcule_le',)


@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = (
        'libelle', 'code', 'famille', 'niveau',
        'probabilite', 'cote_juste', 'resultat',
    )
    list_filter = ('niveau', 'resultat', 'famille', 'origine')
    search_fields = ('libelle', 'code')
    readonly_fields = ('regle_le',)


@admin.register(Cote)
class CoteAdmin(admin.ModelAdmin):
    list_display = (
        'match', 'bookmaker', 'marche', 'selection',
        'valeur', 'releve_le',
    )
    list_filter = ('marche', 'bookmaker')


@admin.register(Contexte)
class ContexteAdmin(admin.ModelAdmin):
    list_display = ('match', 'fiabilite', 'source')
    list_filter = ('fiabilite',)


@admin.register(PropositionParis)
class PropositionAdmin(admin.ModelAdmin):
    list_display = ('libelle', 'match', 'auteur', 'confiance', 'created_at')
    search_fields = ('libelle', 'auteur__username')


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('proposition', 'user', 'choix', 'created_at')
    list_filter = ('choix',)


@admin.register(VoteOption)
class VoteOptionAdmin(admin.ModelAdmin):
    list_display = ('option', 'user', 'choix', 'created_at')
    list_filter = ('choix',)
