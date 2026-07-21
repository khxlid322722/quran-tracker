def static_version(request):
    return {'STATIC_VERSION': '5'}


def no_cache_html(get_response):
    def middleware(request):
        response = get_response(request)
        content_type = response.get('Content-Type', '')
        if 'text/html' in content_type or 'application/manifest+json' in content_type:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
        return response
    return middleware
