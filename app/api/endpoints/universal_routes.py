from fastapi import APIRouter, Request, HTTPException, Depends, Response
from fastapi.responses import StreamingResponse, JSONResponse
import httpx
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.universal_converter import universal_converter
from app.api import deps
from app.core.database import get_db
from app.services.gemini_service import gemini_service
from app.services.claude_service import claude_service
from fastapi import BackgroundTasks

router = APIRouter()

async def get_openai_client():
    return httpx.AsyncClient(base_url="https://api.openai.com/v1", timeout=60.0, follow_redirects=True)

@router.api_route("/{provider}/{path:path}", methods=["GET", "POST", "OPTIONS"])
async def universal_proxy(
    provider: str,
    path: str,
    request: Request,
    key_info: tuple = Depends(deps.get_official_key_from_proxy),
    db: AsyncSession = Depends(get_db)
):
    official_key, user = key_info
    
    # Normalize provider
    provider = provider.lower()
    if provider not in ["openai", "gemini", "claude"]:
        raise HTTPException(status_code=404, detail=f"未知提供商: {provider}")

    # Read body
    try:
        body_bytes = await request.body()
        body = json.loads(body_bytes) if body_bytes else {}
    except json.JSONDecodeError:
        body = {}

    # Determine Request Type (Chat, Models, etc.) based on Path and Body
    # and map to Upstream Endpoint & Format
    
    upstream_url = ""
    target_format = "openai" # default
    upstream_method = request.method
    
    # --- Route Mapping Logic ---
    
    # 1. Target: OpenAI
    if provider == "openai":
        target_format = "openai"
        base_url = "https://api.openai.com/v1"
        
        # Map incoming path to OpenAI path
        if "chat/completions" in path or "messages" in path or "generateContent" in path:
             # It's a chat request
             upstream_path = "chat/completions"
             upstream_method = "POST"
        elif "models" in path:
             upstream_path = "models"
             upstream_method = "GET"
        else:
             upstream_path = path # Try direct pass
             
        upstream_url = f"{base_url}/{upstream_path}"

    # 2. Target: Gemini
    elif provider == "gemini":
        target_format = "gemini"
        base_url = "https://generativelanguage.googleapis.com/v1beta"
        
        # Map to Gemini Path
        if "chat/completions" in path or "messages" in path or "generateContent" in path:
            # Need to extract model. If not in path, check body.
            model = body.get("model", "gemini-1.5-pro")
            # Clean model name if needed (remove 'models/' prefix if present in body but not needed for url construction if we hardcode it, 
            # but Gemini API expects models/{model}:{action})
            if not model.startswith("models/"):
                 # Check if it looks like a gemini model
                 if "gemini" in model:
                      if not model.startswith("models/"): model = f"models/{model}"
                 else:
                      # Default mapping for openai models -> gemini?
                      if "gpt-4" in model: model = "models/gemini-1.5-pro"
                      elif "gpt-3.5" in model: model = "models/gemini-1.0-pro"
                      else: model = "models/gemini-1.5-pro"
            
            action = "streamGenerateContent" if body.get("stream", False) or "stream" in path else "generateContent"
            upstream_path = f"{model}:{action}"
            upstream_method = "POST"
        elif "models" in path:
             upstream_path = "models"
             upstream_method = "GET"
        else:
             upstream_path = path

        upstream_url = f"{base_url}/{upstream_path}"

    # 3. Target: Claude
    elif provider == "claude":
        target_format = "claude"
        base_url = "https://api.anthropic.com/v1"
        
        if "chat/completions" in path or "messages" in path or "generateContent" in path:
            upstream_path = "messages"
            upstream_method = "POST"
        else:
            upstream_path = path
            
        upstream_url = f"{base_url}/{upstream_path}"

    # --- Conversion ---
    
    # Convert Request Body
    # Note: convert_request handles "same format" pass-through internally
    converted_body, from_format = await universal_converter.convert_request(body, target_format, request)
    
    # Prepare Headers
    req_headers = {k: v for k, v in request.headers.items() if k.lower() not in ["host", "content-length", "authorization", "connection", "accept-encoding"]}
    
    # Auth Headers
    if provider == "openai":
        req_headers["Authorization"] = f"Bearer {official_key}"
    elif provider == "gemini":
        req_headers["x-goog-api-key"] = official_key
    elif provider == "claude":
        req_headers["x-api-key"] = official_key
        req_headers["anthropic-version"] = req_headers.get("anthropic-version", "2023-06-01")

    # Make Request
    # Use temporary client or service clients
    local_client = None
    client = None
    
    if provider == "gemini":
        client = gemini_service.client
    elif provider == "claude":
        client = claude_service.client
    else:
        local_client = httpx.AsyncClient(timeout=60.0)
        client = local_client
    
    try:
        req = client.build_request(
            upstream_method,
            upstream_url,
            headers=req_headers,
            json=converted_body,
            params=request.query_params
        )
        
        response = await client.send(req, stream=True)
        
        # If path contained "generateContent" -> expects Gemini
        
        # Default to the provider's native format (Critical for Transparent Mode)
        client_expects = provider
        
        # Override only if path strongly suggests another format (Cross-Provider usage)
        if "chat/completions" in path:
             client_expects = "openai"
        elif "messages" in path and provider != "claude":
             client_expects = "claude"
        elif "generateContent" in path and provider != "gemini":
             client_expects = "gemini"
        
        # Check if stream was requested (check body AND path)
        is_stream = body.get("stream", False)
        if "stream" in path or "streamGenerateContent" in path:
            is_stream = True

        # If "Pass-Through" (client format == target format), convert_request handled request.
        # Response should also be passed through.
        if client_expects == target_format:
             # Pass through streaming response
             return StreamingResponse(
                 response.aiter_bytes(),
                 status_code=response.status_code,
                 headers={k: v for k, v in response.headers.items() if k.lower() not in ["content-length", "content-encoding", "transfer-encoding", "connection"]},
                 background=BackgroundTasks().add_task(response.aclose) if local_client is None else None 
             )
        
        # If conversion needed, we likely need to consume the stream, convert, and re-stream or return JSON
        
        if is_stream:
             # Stream Conversion Generator
             async def stream_converter():
                 try:
                     async for chunk_bytes in response.aiter_bytes():
                         try:
                             chunk_str = chunk_bytes.decode('utf-8')
                             # This assumes chunk is a complete JSON or SSE event lines.
                             # Often it is "data: {...}"
                             # We need to parse SSE.
                             
                             lines = chunk_str.split('\n')
                             for line in lines:
                                 if line.startswith("data: ") and line.strip() != "data: [DONE]":
                                     json_str = line[6:]
                                     try:
                                         data = json.loads(json_str)
                                         
                                         # Convert chunk
                                         converted_chunk = None
                                         if target_format == "gemini" and client_expects == "openai":
                                             converted_chunk = universal_converter.gemini_to_openai_chunk(data, model="gemini-proxy")
                                         elif target_format == "claude" and client_expects == "openai":
                                             converted_chunk = universal_converter.claude_to_openai_chunk(data, model="claude-proxy")
                                         # Add other combinations as needed
                                         
                                         if converted_chunk:
                                             yield f"data: {json.dumps(converted_chunk)}\n\n"
                                         else:
                                             # Fallback or unknown
                                             yield line + "\n"
                                     except:
                                         yield line + "\n"
                                 else:
                                     yield line + "\n"
                         except:
                             yield chunk_bytes # Fallback
                 finally:
                     await response.aclose()

             return StreamingResponse(stream_converter(), media_type="text/event-stream")
        else:
             # Full JSON Conversion
             try:
                 content = await response.read()
                 await response.aclose()
                 
                 # Check for non-200 status first
                 if response.status_code >= 400:
                     # Try to parse error
                     try:
                         data = json.loads(content)
                         # Convert error if possible
                         return JSONResponse(content=data, status_code=response.status_code)
                     except:
                         return Response(content=content, status_code=response.status_code)

                 data = json.loads(content)
                 
                 converted_response = data
                 if target_format == "gemini" and client_expects == "openai":
                     converted_response = universal_converter.gemini_response_to_openai_response(data, model="gemini-proxy")
                 elif target_format == "claude" and client_expects == "openai":
                     converted_response = universal_converter.claude_response_to_openai_response(data, model="claude-proxy")
                 elif target_format == "openai" and client_expects == "gemini":
                     converted_response = universal_converter.openai_response_to_gemini_response(data)
                
                 return JSONResponse(content=converted_response)
             except json.JSONDecodeError:
                 # If response is not JSON (e.g. 404 HTML), return raw content
                 return Response(content=content, status_code=response.status_code)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=502, detail=f"通用代理错误: {str(e)}")
    finally:
        if local_client:
            await local_client.aclose()