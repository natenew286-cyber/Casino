from django.http import JsonResponse
from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Simple health check endpoint to verify the service is up.
    Checks database connection as well.
    """
    health_status = {
        'status': 'ok',
        'database': 'unknown'
    }
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status['database'] = 'connected'
        return JsonResponse(health_status)
    except Exception as e:
        health_status['status'] = 'error'
        health_status['database'] = 'disconnected'
        health_status['error'] = str(e)
        return JsonResponse(health_status, status=503)
