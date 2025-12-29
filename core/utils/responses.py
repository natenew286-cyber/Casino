from rest_framework.response import Response


class SuccessResponse(Response):
    def __init__(self, data=None, message='Success', status=200, **kwargs):
        response_data = {
            'success': True,
            'message': message,
            'data': data or {}
        }
        # Ensure Content-Type is set to application/json
        kwargs.setdefault('content_type', 'application/json')
        super().__init__(response_data, status=status, **kwargs)


class ErrorResponse(Response):
    def __init__(self, message='Error', status=400, errors=None, **kwargs):
        response_data = {
            'success': False,
            'message': message,
            'errors': errors or {}
        }
        # Ensure Content-Type is set to application/json
        kwargs.setdefault('content_type', 'application/json')
        super().__init__(response_data, status=status, **kwargs)