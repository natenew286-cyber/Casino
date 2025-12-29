from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        message = f'Successfully retrieved {len(data)} item(s) from page {self.page.number} of {self.page.paginator.num_pages}. Total items: {self.page.paginator.count}'
        return Response({
            'success': True,
            'message': message,
            'pagination': {
                'count': self.page.paginator.count,
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
                'page_size': self.get_page_size(self.request),
                'current_page': self.page.number,
                'total_pages': self.page.paginator.num_pages
            },
            'data': data
        }, content_type='application/json')