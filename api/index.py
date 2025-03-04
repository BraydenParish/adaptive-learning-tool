from app import handler
from vercel_python import vercel_request, vercel_response

def application(request, context):
    return vercel_request(handler, request, context)
