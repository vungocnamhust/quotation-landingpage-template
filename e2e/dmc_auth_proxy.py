"""Minimal auth_request upstream used only by the Compose DMC gateway proof."""
from fastapi import FastAPI, Request, Response


app = FastAPI()


@app.get("/verify")
async def verify(request: Request) -> Response:
    # Do not consume X-DMC-* from the request.  Nginx must have stripped them
    # before the auth subrequest; this explicit session marker models a valid
    # DMC gateway identity independently of browser-supplied identity headers.
    if request.headers.get("X-DMC-Mock-Session") != "approved":
        return Response(status_code=401)
    return Response(
        status_code=204,
        headers={
            "X-DMC-Email": "gateway-editor@example.test",
            "X-DMC-Person-Id": "dmc-e2e-person",
            "X-DMC-Role": "quotation_editor",
        },
    )
