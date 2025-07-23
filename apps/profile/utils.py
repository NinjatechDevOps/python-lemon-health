def api_response(success: bool, message: str, data: dict = None):
    return {
        "success": success,
        "message": message,
        "data": data or {}
    }

def api_error_response(message: str, status_code: int = 400, data: dict = None):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": message,
            "data": data or {}
        }
    ) 