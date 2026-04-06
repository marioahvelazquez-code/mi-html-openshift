from django.urls import path
from . import views
from .views import subir_excel

urlpatterns = [
    path("entidades/", views.entidades), # Mario: consulta de entidades.
    #Mario: Inicio ruta bitacora.
    path("bitacora/", views.guardar_bitacora_revision),
    #Mario: Fin ruta bitacora.
    #Mario: Inicio ruta reporte excel revision.
    path("bitacora/reporte-excel/", views.generar_reporte_excel_revision),
    #Mario: Fin ruta reporte excel revision.
    path("areas/", views.areas),
    path("temas/", views.temas),
    path("diccionario/", views.diccionario),
    path("subir_excel/", views.subir_excel),
    path("obtener_hojas_excel/", views.obtener_hojas_excel),
]