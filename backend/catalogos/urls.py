from django.urls import path
from . import views

urlpatterns = [
    path("subir_foto/", views.subir_foto),
    path("fotos_cargadas/", views.fotos_cargadas),
]
