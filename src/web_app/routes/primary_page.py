"""

Summary: initial entry point for fast api server...

"""
from fastapi import APIRouter

route=APIRouter()



@route.get("/")
async def base_path():
    """base_path _summary_

    Returns:
        _type_: _description_
    """
    return {"message":"OK"}




