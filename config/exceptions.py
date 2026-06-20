from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.db import IntegrityError


def custom_exception_handler(exc, context):
    """
    Envuelve las excepciones de DRF/Django en una respuesta consistente:
    { "error": True, "detail": <mensaje o dict de errores>, "code": <status> }
    """
    response = exception_handler(exc, context)

    if response is not None:
        response.data = {
            "error": True,
            "detail": response.data,
            "code": response.status_code,
        }
        return response

    if isinstance(exc, IntegrityError):
        return Response(
            {
                "error": True,
                "detail": "Conflicto de integridad: el registro viola una restricción única o de relación.",
                "code": status.HTTP_409_CONFLICT,
            },
            status=status.HTTP_409_CONFLICT,
        )

    # Cualquier otro error no manejado -> 500, pero con formato consistente
    return Response(
        {
            "error": True,
            "detail": str(exc),
            "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
