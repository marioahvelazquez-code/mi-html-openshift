from django.urls import path
from . import views
from .views import subir_excel
from django.conf import settings
from django.conf.urls.static import static
from chatbot import views as chatbot_views

urlpatterns = [
    path("entidades/", views.entidades), # Mario: consulta de entidades.
    path("ficha-nacional/", views.ficha_nacional_archivos),
    path("ficha-estatales/", views.ficha_estatales_archivos),  # Mario: endpoint para resolver fichas estatales dinámicamente.
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
    path('bitacoracarga/', views.bitacoracarga),
    path('login/', views.autenticar_usuario),
    path('getRegion/', views.getRegion),
    path('getEntidad/', views.getEntidad),
    path('getNivelAtencion/', views.getNivelAtencion),
    path('getUnidad/', views.getUnidad),  
    path('getGeneraFicha/', views.getGeneraFicha),  
    path('getGeneraFichaPresidencial/', views.getGeneraFichaPresidencial),  
    path('getGeneraFichaPresidencialLote/', views.getGeneraFichaPresidencialLote),  

    path('solicitud-acceso-bd/', views.guardar_solicitud_acceso_bd),
    path('solicitud-especial-bd/', views.guardar_solicitud_especial_bd),
    path('chatbot-query/', views.chatbot_query),
    path('buscar-hospitales/', chatbot_views.buscar_hospitales),
    path('buscar-variables/', chatbot_views.buscar_variables),
    path('chatbot/', chatbot_views.chatbot),    
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
