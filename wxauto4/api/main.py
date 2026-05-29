"""wxauto4 REST API server.

Start with:
    python -m wxauto4.api.main
    python -m wxauto4.api.main --port 8765
    python -m wxauto4.api.main --token SECRET
"""
from __future__ import annotations
import argparse
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from wxauto4.api.routes.wechat import router as wechat_router

app = FastAPI(
    title="wxauto4 API",
    description="Local HTTP API for WeChat 4.x automation via wxauto4",
    version="1.0.0",
)

# CORS: only allow localhost by default
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1", "http://localhost"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional API token
_api_token: str | None = None


@app.middleware("http")
async def check_token(request: Request, call_next):
    if _api_token:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {_api_token}":
            raise HTTPException(401, "Invalid or missing API token")
    return await call_next(request)


@app.get("/health")
def health():
    return {"ok": True, "service": "wxauto4"}


app.include_router(wechat_router)


def main():
    parser = argparse.ArgumentParser(description="wxauto4 REST API server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8760, help="Port (default: 8760)")
    parser.add_argument("--token", default=None, help="API token for authentication")
    args = parser.parse_args()

    global _api_token
    _api_token = args.token

    print(f"Starting wxauto4 API on {args.host}:{args.port}")
    if _api_token:
        print("Token authentication enabled")

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
