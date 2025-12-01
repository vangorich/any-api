from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import StreamingResponse
import httpx
from app.api import deps

router = APIRouter()

@router.api_route("/{target_url:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def generic_proxy(target_url: str, request: Request):
    """
    Generic proxy for third-party APIs.
    Format: /http(s)://(url)/...
    """
    # Check if target_url starts with http
    if not (target_url.startswith("http://") or target_url.startswith("https://")):
        # If not, it might be a normal API call that fell through, or invalid
        # But since this is mounted at root level (if we do), it might catch everything.
        # We should probably mount this specifically or handle it carefully.
        # For now, let's assume this router is included with a prefix or we check carefully.
        # If we mount it at root, we need to be careful not to shadow other routes.
        # But the requirement says: http(s)://(url)/http(s)://(url)/v1
        # This implies the server address is the first part.
        # So the path is literally `http://...` which is weird for standard web servers.
        # Usually it's `proxy/http://...` or similar.
        # But if the user means `http://myserver.com/https://api.openai.com/v1`
        # Then the path received by FastAPI is `https://api.openai.com/v1`.
        # FastAPI strips the host.
        # So `target_url` will be `https://api.openai.com/v1`.
        pass

    if not (target_url.startswith("http://") or target_url.startswith("https://")):
         raise HTTPException(status_code=404, detail="Not found")

    # Extract method, headers, body
    method = request.method
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)
    
    body = await request.body()
    
    # Create client
    # NOTE: We cannot use 'async with' here because we need the client to stay open
    # for the StreamingResponse. We must close it manually in the generator.
    client = httpx.AsyncClient(follow_redirects=True)
    
    try:
        req = client.build_request(
            method,
            target_url,
            headers=headers,
            content=body,
            params=request.query_params
        )
        
        response = await client.send(req, stream=True)
        
        async def safe_stream_generator(response, client):
            try:
                async for chunk in response.aiter_bytes():
                    yield chunk
            except (httpx.ReadError, httpx.ConnectError) as e:
                # Log the error but don't crash the server
                print(f"Generic proxy stream error: {e}")
            except Exception as e:
                print(f"Unexpected generic proxy stream error: {e}")
            finally:
                await response.aclose()
                await client.aclose()

        return StreamingResponse(
            safe_stream_generator(response, client),
            status_code=response.status_code,
            headers=dict(response.headers),
            background=None
        )
    except Exception as e:
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"Proxy error: {e}")
