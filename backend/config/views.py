from django.http import JsonResponse
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT 1")

def api_test(request):
    return JsonResponse({"status": "ok", "message": "API viva"})
