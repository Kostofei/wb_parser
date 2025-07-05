from rest_framework import filters

class MultiFieldSearchFilter(filters.SearchFilter):
    def get_search_fields(self, view, request):
        # Возвращаем разные поля в зависимости от параметров запроса
        if 'title' in request.query_params:
            return ['title']
        if 'description' in request.query_params:
            return ['description']
        if 'rating' in request.query_params:
            return ['rating']
        return super().get_search_fields(view, request)