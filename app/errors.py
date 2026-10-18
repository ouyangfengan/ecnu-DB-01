from fastapi.responses import JSONResponse


class APIError(Exception):
    def __init__(self, code: int, message: str, status: int):
        self.code = code
        self.message = message
        self.status = status


def success(data=None, message: str = "ok"):
    return {"code": 0, "msg": message, "data": {} if data is None else data}


def failure(code: int, message: str, status: int):
    headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
    return JSONResponse(
        status_code=status,
        content={"code": code, "msg": message, "data": {}},
        headers=headers,
    )
