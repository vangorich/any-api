import json
import httpx
import logging
from typing import Optional, Any, Dict
from fastapi import Request, Response, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from app.core.config import settings
from app.services.universal_converter import universal_converter
from app.services.gemini_service import gemini_service
from app.services.claude_service import claude_service

# 强制配置 logger 输出到控制台，确保用户能看到日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# 额外添加一个 StreamHandler 以防 basicConfig 不生效
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

class ProxyService:
    def identify_target_provider(self, key: str) -> str:
        """
        根据 Key 前缀识别目标服务商
        """
        if key.startswith("sk-ant-"):
            return "claude"
        elif key.startswith("AIza"):
            return "gemini"
        elif key.startswith("sk-"):
            return "openai"
        # 默认回退到 OpenAI，或者可以根据配置调整
        return "openai"

    async def smart_proxy_handler(
        self,
        request: Request,
        path: str,
        official_key: str,
        incoming_format: str,  # "openai", "gemini", "claude"
        background_tasks: BackgroundTasks = None
    ):
        target_provider = self.identify_target_provider(official_key)
        masked_key = f"{official_key[:8]}...{official_key[-4:]}" if len(official_key) > 12 else "***"
        
        # 使用 print 确保在所有环境下可见
        print(f"DEBUG: [Proxy] Route Decision: Incoming={incoming_format}, Target={target_provider}, Key={masked_key}")
        logger.info(f"[Proxy] Route Decision: Incoming={incoming_format}, Target={target_provider}, Key={masked_key}")
        
        # 1. 透传模式 (Pass-through)
        if incoming_format == target_provider:
            print(f"DEBUG: [Proxy] Mode: PASS-THROUGH ({target_provider.upper()})")
            return await self._handle_passthrough(request, path, official_key, target_provider)
        
        # 2. 转换模式 (Conversion)
        print(f"DEBUG: [Proxy] Mode: CONVERSION ({incoming_format.upper()} -> {target_provider.upper()})")
        return await self._handle_conversion(request, path, official_key, incoming_format, target_provider)

    async def _handle_passthrough(
        self,
        request: Request,
        path: str,
        key: str,
        provider: str
    ):
        """处理同构透传请求"""
        # 构建目标 URL
        base_url = ""
        target_path = path
        
        if provider == "openai":
            base_url = "https://api.openai.com"
            # 如果 path 已经是完整路径则保持，否则拼接。
            #通常传入的 path 是去除前缀后的，例如 "chat/completions"
            if not path.startswith("/"):
                target_path = f"/v1/{path}"
            else:
                target_path = path # 假设传入的已经是 /v1/... 或者调用者处理好
                
        elif provider == "gemini":
            base_url = "https://generativelanguage.googleapis.com"
            # Gemini 通常是 /v1beta/...
            if not path.startswith("/"):
                target_path = f"/v1beta/{path}"
            else:
                target_path = path

        elif provider == "claude":
            base_url = "https://api.anthropic.com"
            if not path.startswith("/"):
                target_path = f"/v1/{path}"
            else:
                target_path = path

        target_url = f"{base_url}{target_path}"
        
        # 处理 Headers
        excluded_headers = {"host", "content-length", "connection", "accept-encoding", "transfer-encoding"}
        headers = {k: v for k, v in request.headers.items() if k.lower() not in excluded_headers}
        
        # 注入 Key
        if provider == "openai":
            headers["Authorization"] = f"Bearer {key}"
        elif provider == "gemini":
            # Gemini 可以用 header x-goog-api-key 或者 query param key
            headers["x-goog-api-key"] = key
            # 移除 Authorization 避免冲突
            if "Authorization" in headers:
                del headers["Authorization"]
        elif provider == "claude":
            headers["x-api-key"] = key
            headers["anthropic-version"] = headers.get("anthropic-version", "2023-06-01")
            if "Authorization" in headers:
                del headers["Authorization"]

        # 准备 Body
        body = await request.body()
        
        # 准备 Query Params
        params = dict(request.query_params)
        if provider == "gemini":
            params["key"] = key # Gemini 也支持 query param，双重保险

        # 获取 Client
        client = self._get_client(provider)
        
        try:
            logger.info(f"[Proxy] Forwarding request to: {target_url} (Method: {request.method})")
            
            # 构建请求
            # 注意: 如果是 Gemini 并且使用 httpx，需要注意 timeout
            # 这里我们使用 stream=True 来支持流式透传
            
            # 使用 client.build_request 更加灵活
            req = client.build_request(
                request.method,
                target_url,
                headers=headers,
                content=body,
                params=params,
                timeout=120.0
            )
            
            response = await client.send(req, stream=True)
            logger.info(f"[Proxy] Upstream response status: {response.status_code}")
            
            # 错误处理透传
            if response.status_code >= 400:
                error_content = await response.aread()
                print(f"DEBUG: [Proxy] Upstream error (Pass-through): Status={response.status_code}, Body={error_content[:500]}")
                logger.warning(f"[Proxy] Upstream error: {error_content[:200]}...")
                await response.aclose()
                return Response(
                    content=error_content,
                    status_code=response.status_code,
                    media_type=response.headers.get("content-type")
                )

            # 流式响应透传
            excluded_response_headers = {"content-encoding", "content-length", "transfer-encoding", "connection"}
            response_headers = {k: v for k, v in response.headers.items() if k.lower() not in excluded_response_headers}

            async def stream_generator(response: httpx.Response):
                """一个显式的异步生成器，用于强制流式传输，避免缓冲。"""
                try:
                    async for chunk in response.aiter_bytes():
                        yield chunk
                except Exception as e:
                    logger.error(f"[Proxy] Pass-through stream error: {e}")
                finally:
                    await response.aclose()

            return StreamingResponse(
                stream_generator(response),
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get("content-type")
            )
            
        except httpx.RequestError as e:
            logger.error(f"Proxy request failed: {e}")
            raise HTTPException(status_code=502, detail=f"Upstream service error: {str(e)}")


    async def _handle_conversion(
        self,
        request: Request,
        path: str,
        key: str,
        incoming_format: str,
        target_provider: str
    ):
        """处理异构转换请求"""
        # 1. 读取并解析 Body
        try:
            body_bytes = await request.body()
            body = json.loads(body_bytes) if body_bytes else {}
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON body")

        # 2. 转换请求体 (Incoming -> Target)
        converted_body, _ = await universal_converter.convert_request(body, target_provider, request)
        
        # 3. 确定目标 URL 和 Method
        # 这里需要基于 target_provider 和原始意图(如 chat/completions) 映射到目标 path
        target_url = ""
        target_method = request.method
        stream = body.get("stream", False)
        
        logger.info(f"[Proxy] Converting body... (Stream={stream})")
        
        # 简单映射逻辑 (主要针对 chat/completions 场景)
        if target_provider == "gemini":
            # OpenAI/Claude -> Gemini
            # 1. 优先从原始 body 中获取 model，因为转换后的 body 可能已移除了 model 字段
            raw_model = body.get("model", "")
            
            # 2. 如果原始 body 没 model，尝试从 converted_body 获取（作为 fallback）
            if not raw_model:
                raw_model = converted_body.get("model", "gemini-1.5-pro")
                
            model = raw_model
            original_model = model
            
            # 3. 智能模型映射逻辑
            if not "gemini" in model.lower():
                # 如果用户明确传了非 Gemini 模型（如 gpt-4），才进行映射
                # 如果用户传的是 gemini-2.0-flash-exp，则保持原样
                if "gpt-3.5" in model:
                    model = "gemini-1.5-flash"
                elif "gpt-4" in model:
                    model = "gemini-1.5-pro"
                else:
                    # 对于未知的模型名称，默认使用 gemini-1.5-pro，或者您可以选择保持原样尝试请求
                    # 这里为了兼容性，如果不包含 gemini 且不是 gpt 系列，我们暂且信任用户想用 gemini-1.5-pro 兜底
                    # 但为了灵活性，如果它看起来像是一个具体的模型名，或许应该保留？
                    # 现阶段保持映射到 pro 以防乱传参数导致 404
                    model = "gemini-1.5-pro"
                
                logger.info(f"[Proxy] Model Mapped: {original_model} -> {model}")
            else:
                # 如果包含 gemini，直接使用用户指定的模型 (e.g. gemini-2.0-flash-exp)
                logger.info(f"[Proxy] Using user-specified Gemini model: {model}")
            
            # 格式化模型名称
            if not model.startswith("models/"):
                model = f"models/{model}"

            action = "streamGenerateContent" if stream else "generateContent"
            target_url = f"https://generativelanguage.googleapis.com/v1beta/{model}:{action}"
            target_method = "POST"
            
            # 清理 Gemini 不支持的字段
            if "model" in converted_body: del converted_body["model"]
            if "stream" in converted_body: del converted_body["stream"]

        elif target_provider == "claude":
            # OpenAI/Gemini -> Claude
            target_url = "https://api.anthropic.com/v1/messages"
            target_method = "POST"
            
            # 智能模型映射
            current_model = converted_body.get("model", "")
            if not current_model.startswith("claude-"):
                # 默认映射到一个通用的强模型
                converted_body["model"] = "claude-3-5-sonnet-20240620"
            
        elif target_provider == "openai":
            # Gemini/Claude -> OpenAI
            target_url = "https://api.openai.com/v1/chat/completions"
            target_method = "POST"

        # 4. 准备 Headers
        headers = {k: v for k, v in request.headers.items() if k.lower() not in ["host", "content-length", "authorization", "x-api-key", "x-goog-api-key"]}
        headers["Content-Type"] = "application/json"
        
        if target_provider == "openai":
            headers["Authorization"] = f"Bearer {key}"
        elif target_provider == "gemini":
            headers["x-goog-api-key"] = key
        elif target_provider == "claude":
            headers["x-api-key"] = key
            headers["anthropic-version"] = "2023-06-01"

        # 5. 发送请求
        client = self._get_client(target_provider)
        
        try:
            req = client.build_request(
                target_method,
                target_url,
                headers=headers,
                json=converted_body,
                timeout=120.0
            )
            
            response = await client.send(req, stream=True)
            
            # 6. 处理响应转换
            
            if response.status_code >= 400:
                # 错误处理
                error_content = await response.aread()
                await response.aclose()
                # 尝试转换错误格式 (Todo: 完善 ErrorConverter)
                return Response(content=error_content, status_code=response.status_code)

            if stream:
                # 流式转换
                return StreamingResponse(
                    self._stream_converter(response, target_provider, incoming_format, original_model),
                    media_type="text/event-stream"
                )
            else:
                # 非流式转换
                resp_content = await response.aread()
                await response.aclose()
                try:
                    resp_json = json.loads(resp_content)
                    final_response = None
                    
                    # 简化：只处理最常见的 OpenAI 互转
                    # 实际应完善 universal_converter 的响应转换
                    if incoming_format == "openai":
                        if target_provider == "gemini":
                            final_response = universal_converter.gemini_response_to_openai_response(resp_json, model="gemini-proxy")
                        elif target_provider == "claude":
                            final_response = universal_converter.claude_response_to_openai_response(resp_json, model="claude-proxy")
                    elif incoming_format == "gemini":
                        if target_provider == "openai":
                            final_response = universal_converter.openai_response_to_gemini_response(resp_json)
                    
                    if final_response:
                        return JSONResponse(final_response)
                    else:
                        # Fallback: return raw
                        return JSONResponse(resp_json)
                        
                except json.JSONDecodeError:
                    return Response(content=resp_content, status_code=response.status_code)

        except httpx.RequestError as e:
            logger.error(f"Conversion request failed: {e}")
            raise HTTPException(status_code=502, detail=f"Upstream service error: {str(e)}")

    async def _stream_converter(self, response: httpx.Response, from_provider: str, to_format: str, original_model: str):
        """流式响应转换生成器，现在能处理 JSON Stream 和完整的 JSON 数组"""
        buffer = ""
        brace_level = 0
        in_string = False
        
        try:
            async for line in response.aiter_lines():
                print(f"DEBUG: [Proxy] Raw Stream Line: {line}")
                buffer += line.strip()

                # 移除可能存在于对象之间的逗号
                if buffer.startswith(','):
                    buffer = buffer[1:]

                # 兼容完整的JSON数组格式
                if buffer.startswith('[') and buffer.endswith(']'):
                    try:
                        gemini_chunks = json.loads(buffer)
                        for chunk in gemini_chunks:
                            if to_format == "openai":
                                openai_chunk = universal_converter.gemini_to_openai_chunk(chunk, original_model)
                                if openai_chunk:
                                    yield f"data: {json.dumps(openai_chunk)}\n\n"
                        buffer = "" # 清空，准备下次请求
                        continue
                    except json.JSONDecodeError:
                        # 可能是数组还不完整，继续累积
                        pass

                # 处理 JSON Stream (多个独立的 JSON 对象)
                while True:
                    start_brace = buffer.find('{')
                    if start_brace == -1:
                        break # 缓冲区没有 JSON 对象了

                    brace_level = 0
                    in_string = False
                    end_brace = -1

                    for i in range(start_brace, len(buffer)):
                        char = buffer[i]
                        if char == '"':
                            # 简单的字符串转义处理
                            if i > 0 and buffer[i-1] != '\\':
                                in_string = not in_string
                        
                        if not in_string:
                            if char == '{':
                                brace_level += 1
                            elif char == '}':
                                brace_level -= 1
                        
                        if brace_level == 0 and i >= start_brace:
                            end_brace = i
                            break
                    
                    if end_brace != -1:
                        # 找到了一个完整的 JSON 对象
                        json_str = buffer[start_brace : end_brace + 1]
                        buffer = buffer[end_brace + 1:] # 更新缓冲区
                        
                        try:
                            chunk = json.loads(json_str)
                            if to_format == "openai":
                                openai_chunk = universal_converter.gemini_to_openai_chunk(chunk, original_model)
                                if openai_chunk:
                                    yield f"data: {json.dumps(openai_chunk)}\n\n"
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to decode JSON object from stream: {json_str}")
                            # 继续处理缓冲区的剩余部分
                    else:
                        break # 没有找到完整的 JSON 对象，需要更多数据
            
            # 确保流结束后发送 [DONE]
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"[Proxy] Stream conversion error: {e}", exc_info=True)
        finally:
            await response.aclose()


    def _get_client(self, provider: str) -> httpx.AsyncClient:
        if provider == "gemini":
            return gemini_service.client
        elif provider == "claude":
            return claude_service.client
        else:
            # 对于 OpenAI，我们可能没有持久化的全局 client，或者可以使用一个
            return httpx.AsyncClient(timeout=60.0)

proxy_service = ProxyService()