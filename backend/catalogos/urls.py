from django.urls import path
from . import views

urlpatterns = [
    path("guardar_inicio_operaciones/", views.guardar_inicio_operaciones),
    path("descargar_bitacora/", views.descargar_bitacora),
]
