class SimpleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.
        print("Initializing middleware")

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        print("Middleware pre-processing")

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.
        print("Middleware post-processing")

        return response
