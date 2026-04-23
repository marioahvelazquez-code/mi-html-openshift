from django.urls import path

from . import views

urlpatterns = [
    path("autenticar/", views.autenticar_usuario),
    path("cambiar-password-primer-ingreso/", views.cambiar_password_primer_ingreso),
    path("login/", views.login_usuarios),
    path("entidades/", views.listar_entidades),
    path("bitacora/", views.bitacora_revision),
    path("bitacora/reporte-excel/", views.reporte_excel_bitacora),
]