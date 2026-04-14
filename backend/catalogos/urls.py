from django.urls import path
from . import views

urlpatterns = [
    path("subir_foto/", views.subir_foto),
    path("fotos_cargadas/", views.fotos_cargadas),
    path("listar_fotos/", views.listar_fotos),
    path("descargar_foto/<str:nombre>/", views.descargar_foto),
    path("descargar_bitacora/", views.descargar_bitacora),
]
