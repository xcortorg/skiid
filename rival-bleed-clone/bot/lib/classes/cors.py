from typing import Iterable, Dict, FrozenSet
from collections import defaultdict
from sanic import Sanic, response
from sanic.router import Route

# Function to add CORS headers to responses
def _add_cors_headers(response, methods: Iterable[str]) -> None:
    allow_methods = list(set(methods))
    if "OPTIONS" not in allow_methods:
        allow_methods.append("OPTIONS")
    
    # CORS headers configuration
    headers = {
        "Access-Control-Allow-Methods": ",".join(allow_methods),
        "Access-Control-Allow-Origin": "*",  # Allow all origins (you can restrict this to a specific domain)
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Headers": (
            "origin, content-type, accept, "
            "authorization, x-xsrf-token, x-request-id"
        ),
        "Access-Control-Expose-Headers": "*",  # Exposing all headers
    }
    response.headers.extend(headers)

# Function to add CORS headers to non-OPTIONS requests
def add_cors_headers(request, response):
    if request.method != "OPTIONS":
        methods = [method for method in request.route.methods]
        _add_cors_headers(response, methods)

# Compile a list of routes that need OPTIONS method added for CORS
def _compile_routes_needing_options(routes: Dict[str, Route]) -> Dict[str, FrozenSet]:
    needs_options = defaultdict(list)
    
    # Add OPTIONS method to routes missing it
    for route in routes.values():
        if "OPTIONS" not in route.methods:
            needs_options[route.uri].extend(route.methods)

    return {
        uri: frozenset(methods) for uri, methods in dict(needs_options).items()
    }

# Wrapper for OPTIONS handler
def _options_wrapper(handler, methods):
    def wrapped_handler(request, *args, **kwargs):
        return handler(request, methods)
    return wrapped_handler

# Actual OPTIONS handler that adds the CORS headers
async def options_handler(request, methods) -> response.HTTPResponse:
    resp = response.empty()
    _add_cors_headers(resp, methods)
    return resp

# Setup CORS by adding OPTIONS routes where necessary
def setup_options(app: Sanic, _):
    app.router.reset()
    needs_options = _compile_routes_needing_options(app.router.routes_all)
    
    for uri, methods in needs_options.items():
        # Add an OPTIONS route for URIs that need it
        app.add_route(
            _options_wrapper(options_handler, methods),
            uri,
            methods=["OPTIONS"],
        )
    
    app.router.finalize()