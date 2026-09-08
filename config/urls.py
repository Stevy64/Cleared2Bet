from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.http import FileResponse
from django.urls import include, path, re_path

from paris import views

admin.site.site_header = 'Cleared2Bet'
admin.site.site_title = 'Cleared2Bet'
admin.site.index_title = 'Saisie et consultation'


def service_worker(request):
    chemin = Path(settings.BASE_DIR) / 'static' / 'sw.js'
    resp = FileResponse(chemin.open('rb'), content_type='application/javascript')
    resp['Service-Worker-Allowed'] = '/'
    resp['Cache-Control'] = 'no-cache'
    return resp


def manifest(request):
    chemin = Path(settings.BASE_DIR) / 'static' / 'manifest.webmanifest'
    return FileResponse(chemin.open('rb'), content_type='application/manifest+json')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('paris.urls')),
    path('sw.js', service_worker),
    path('manifest.webmanifest', manifest),
    path('', views.app, name='app'),
    re_path(r'^(?:matchs/\d+|historique|verification|reglages|jour)/?$', views.app),
]
