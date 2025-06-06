"""

evaluation_route.py

This page is responsible for handling the evaluation page route

/evaluation/{index}




"""

from fastapi import APIRouter
from fastapi.responses import FileResponse


route=APIRouter()


# this should be dynamic in terms of eval 
@route.get("/eval/{md}")
def eval_render():
    return FileResponse("src/web_app/static/html/annotation_interface.html")




@route.post("/eval")
def eval_post(payload):
    # todo this shoudl take in a uri, or url for the selected thing, in the normal cycle we do it off the 
    pass



