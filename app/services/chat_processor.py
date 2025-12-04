import json
import time
import httpx
import logging
from typing import AsyncGenerator, Tuple, List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.schemas.openai import ChatCompletionRequest, ChatMessage
from app.services.universal_converter import universal_converter, ApiFormat
from app.core.errors import ErrorConverter
from app.services.variable_service import variable_service
from app.services.regex_service import regex_service
from app.models.user import User
from app.models.key import ExclusiveKey, OfficialKey
from app.models.preset import Preset
from app.models.regex import RegexRule
from app.models.preset_regex import PresetRegexRule
from app.models.log import Log
from app.models.key import count_tokens_for_messages, get_tokenizer
from app.core.config import settings
from sqlalchemy.future import select
from fastapi import Request

logger = logging.getLogger(__name__)

class ChatProcessor:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0)

    async def process_request(
        self,
        request: Request,
        db: AsyncSession,
        official_key: OfficialKey,
        exclusive_key: ExclusiveKey,
        user: User,
        log_level: str,
        model_override: str = None
    ) -> Tuple[Dict[str, Any], int, ApiFormat]:
        start_time = time.time()
        body_bytes = await request.body()
        body = json.loads(body_bytes)
        target_format = "gemini"

        converted_body, original_format = await universal_converter.convert_request(body, "openai", request=request)
        
        if model_override:
            converted_body["model"] = model_override
            
        openai_request = ChatCompletionRequest(**converted_body)
        
        log_entry = await self._create_initial_log(db, exclusive_key, official_key, user, openai_request.model, openai_request.stream, [msg.dict() for msg in openai_request.messages])

        presets, regex_rules, preset_regex_rules = await self._load_context(db, exclusive_key)
        openai_request = self._apply_preprocessing(openai_request, presets, regex_rules, preset_regex_rules)
        final_payload, _ = await universal_converter.convert_request(openai_request.dict(), target_format)
        
        if openai_request.stream:
            return self._logged_stream_generator(
                self.stream_chat_completion(
                    final_payload, target_format, original_format, openai_request.model,
                    official_key.key, regex_rules, preset_regex_rules
                ),
                db=db,
                log_entry=log_entry,
                official_key=official_key,
                start_time=start_time
            )
        else:
            result, status_code, _ = await self.non_stream_chat_completion(
                final_payload, target_format, original_format, openai_request.model,
                official_key.key, regex_rules, preset_regex_rules
            )
            latency = time.time() - start_time
            tokenizer = get_tokenizer(openai_request.model)
            response_content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            output_tokens = len(tokenizer.encode(response_content))
            await self._finalize_log(db, log_entry, official_key, status_code, latency, output_tokens)
            return result, status_code, original_format

    async def _load_context(self, db: AsyncSession, exclusive_key: ExclusiveKey) -> Tuple[List, List, List]:
        """从数据库加载预设和正则规则
        
        修改说明：
        - 现在直接从 PresetItem 表读取预设项，而不是从 Preset.content 读取
        - 这确保了数据的一致性，并支持 history 类型
        - 向后兼容：如果 PresetItem 为空，可以回退到 Preset.content
        """
        presets, regex_rules, preset_regex_rules = [], [], []
        
        if exclusive_key.preset_id:
            # 使用 selectinload 预加载关联的 items，避免 N+1 查询
            result = await db.execute(
                select(Preset)
                .options(selectinload(Preset.items))
                .filter(Preset.id == exclusive_key.preset_id)
            )
            preset = result.scalars().first()
            
            if preset:
                # 直接使用 PresetItem 表中的数据
                if preset.items:
                    # 按 sort_order 排序
                    sorted_items = sorted(preset.items, key=lambda x: x.sort_order)
                    
                    items_data = []
                    for item in sorted_items:
                        items_data.append({
                            "role": item.role,
                            "type": item.type,
                            "content": item.content,
                            "enabled": item.enabled,
                            "order": item.sort_order,
                            "name": item.name,
                        })
                    
                    presets.append({
                        "id": preset.id,
                        "name": preset.name,
                        "items": items_data
                    })
                else:
                    # 向后兼容：如果 PresetItem 表为空，尝试从 Preset.content 读取
                    # 这支持老客户端的数据迁移
                    if preset.content:
                        try:
                            content_data = json.loads(preset.content) if isinstance(preset.content, str) else preset.content
                            items = content_data.get('preset') or content_data.get('items', [])
                            if items:
                                presets.append({
                                    "id": preset.id,
                                    "name": preset.name,
                                    "items": items
                                })
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning(f"预设 {preset.id} 的 content 解析失败: {e}")
                
                # 加载预设关联的正则规则
                result = await db.execute(
                    select(PresetRegexRule).filter(
                        PresetRegexRule.preset_id == preset.id,
                        PresetRegexRule.is_active == True
                    )
                )
                preset_regex_rules = result.scalars().all()
        
        # 加载全局正则规则
        if exclusive_key.enable_regex:
            result = await db.execute(
                select(RegexRule).filter(RegexRule.is_active == True)
            )
            regex_rules = result.scalars().all()
        
        return presets, regex_rules, preset_regex_rules

    def _apply_preprocessing(
        self,
        request: ChatCompletionRequest,
        presets: List,
        global_rules: List,
        local_rules: List
    ) -> ChatCompletionRequest:
        """应用所有前置处理: 全局正则 -> 局部正则 -> 预设 -> 变量
        
        修改说明（第2步）：
        - 改进了预设项的处理逻辑
        - 修复了历史消息的类型转换问题
        - 添加了更详细的错误处理和日志
        - 支持 normal、user_input、history 三种类型
        - 使用 _safe_content_to_string 安全转换内容
        """
        # 1. 应用正则
        global_pre = [r for r in global_rules if r.type == "pre"]
        local_pre = [r for r in local_rules if r.type == "pre"]
        for msg in request.messages:
            if isinstance(msg.content, str):
                msg.content = regex_service.process(msg.content, global_pre)
                msg.content = regex_service.process(msg.content, local_pre)

        # 2. 应用预设
        if presets and request.messages:
            for preset in presets:
                try:
                    items = preset.get('items', [])
                    if not items:
                        logger.debug(f"预设 {preset.get('name')} 没有预设项")
                        continue

                    # 按 order 排序预设项
                    sorted_items = sorted(items, key=lambda x: x.get('order', 0))
                    
                    # 保存原始消息用于后续处理
                    original_messages = list(request.messages)
                    
                    # 找到最后一条用户消息
                    last_user_message = None
                    last_user_index = -1
                    for i in range(len(original_messages) - 1, -1, -1):
                        if original_messages[i].role == 'user':
                            last_user_message = original_messages[i]
                            last_user_index = i
                            break
                    
                    # 获取历史消息（除了最后一条用户消息的所有消息）
                    history_messages = []
                    if last_user_index >= 0:
                        history_messages = original_messages[:last_user_index]
                    else:
                        # 如果没有用户消息，所有消息都是历史
                        history_messages = original_messages
                    
                    # 处理预设项
                    processed_messages = []
                    
                    for item in sorted_items:
                        # 检查是否启用
                        if not item.get('enabled', True):
                            logger.debug(f"预设项 {item.get('name')} 已禁用，跳过")
                            continue
                        
                        item_type = item.get('type', 'normal')
                        item_role = item.get('role', 'system')
                        item_content = item.get('content', '')
                        
                        try:
                            if item_type == 'normal':
                                # 普通类型：直接注入
                                processed_messages.append({
                                    'role': item_role,
                                    'content': item_content
                                })
                                logger.debug(f"添加普通预设项: {item.get('name')}")
                                
                            elif item_type == 'user_input':
                                # 用户输入类型：插入最后一条用户消息
                                if last_user_message:
                                    processed_messages.append({
                                        'role': last_user_message.role,
                                        'content': self._safe_content_to_string(last_user_message.content)
                                    })
                                    logger.debug(f"添加用户输入预设项: {item.get('name')}")
                                else:
                                    logger.warning(f"预设项 {item.get('name')} 类型为 user_input，但没有找到用户消息")
                                    
                            elif item_type == 'history':
                                # 历史类型：插入历史对话
                                if history_messages:
                                    for hist_msg in history_messages:
                                        processed_messages.append({
                                            'role': hist_msg.role,
                                            'content': self._safe_content_to_string(hist_msg.content)
                                        })
                                    logger.debug(f"添加历史预设项: {item.get('name')}，包含 {len(history_messages)} 条消息")
                                else:
                                    logger.debug(f"预设项 {item.get('name')} 类型为 history，但没有历史消息")
                            else:
                                logger.warning(f"未知的预设项类型: {item_type}，预设项: {item.get('name')}")
                        
                        except Exception as e:
                            logger.error(f"处理预设项 {item.get('name')} 时出错: {e}", exc_info=True)
                            continue
                    
                    # 如果有处理过的消息，替换原始消息
                    if processed_messages:
                        try:
                            request.messages = [ChatMessage(**msg) for msg in processed_messages]
                            logger.info(f"预设 {preset.get('name')} 应用成功，共处理 {len(processed_messages)} 条消息")
                        except Exception as e:
                            logger.error(f"创建 ChatMessage 对象时出错: {e}", exc_info=True)
                            # 如果转换失败，保持原始消息
                            pass
                    
                except Exception as e:
                    logger.error(f"预设 {preset.get('name')} 处理失败: {e}", exc_info=True)
                    # 继续处理下一个预设，不中断整个流程
                    continue

        # 3. 应用变量
        for msg in request.messages:
            if isinstance(msg.content, str):
                msg.content = variable_service.parse_variables(msg.content)
        
        return request

    def _safe_content_to_string(self, content: Any) -> str:
        """安全地将内容转换为字符串
        
        处理多种内容类型：
        - 字符串：直接返回
        - 字典/列表：转换为 JSON 字符串
        - 其他类型：使用 str() 转换
        
        这个方法解决了历史消息中可能包含复杂对象的问题
        """
        if isinstance(content, str):
            return content
        elif isinstance(content, (dict, list)):
            try:
                return json.dumps(content, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"JSON 序列化失败: {e}，使用 str() 转换")
                return str(content)
        else:
            return str(content)

    def _apply_postprocessing(self, content: str, global_rules: List, local_rules: List) -> str:
        """应用所有后置处理: 局部正则 -> 全局正则"""
        local_post = [r for r in local_rules if r.type == "post"]
        global_post = [r for r in global_rules if r.type == "post"]
        content = regex_service.process(content, local_post)
        content = regex_service.process(content, global_post)
        return content

    async def _create_initial_log(self, db: AsyncSession, exclusive_key: ExclusiveKey, official_key: OfficialKey, user: User, model: str, is_stream: bool, messages: List[Dict[str, Any]]) -> Log:
        input_tokens = count_tokens_for_messages(messages, model)
        
        log_entry = Log(
            exclusive_key_id=exclusive_key.id,
            official_key_id=official_key.id,
            user_id=user.id,
            model=model,
            status="processing",
            status_code=0,
            latency=0, ttft=0,
            is_stream=is_stream,
            input_tokens=input_tokens,
            output_tokens=0
        )
        return log_entry

    async def _finalize_log(self, db: AsyncSession, log_entry: Optional[Log], official_key: OfficialKey, status_code: Any, latency: float, output_tokens: int, ttft: Optional[float] = None):
        if not log_entry or not official_key:
            return

        try:
            try:
                numeric_status_code = int(status_code)
            except (ValueError, TypeError):
                numeric_status_code = 500
            
            log_entry.status_code = numeric_status_code
            log_entry.status = "ok" if 200 <= numeric_status_code < 300 else "error"
            log_entry.latency = latency
            log_entry.ttft = ttft if ttft is not None else latency
            log_entry.output_tokens = output_tokens
            db.add(log_entry)

            official_key.usage_count += 1
            official_key.input_tokens = (official_key.input_tokens or 0) + (log_entry.input_tokens or 0)
            official_key.output_tokens = (official_key.output_tokens or 0) + output_tokens
            official_key.last_status_code = numeric_status_code
            
            if log_entry.status == "error":
                official_key.error_count += 1
                official_key.last_status = str(status_code)
            else:
                official_key.last_status = "active"

            db.add(official_key)
            await db.commit()
            logger.info(f"[ChatProcessor] Finalized log and updated key stats for Official Key ID {official_key.id}")

        except Exception as e:
            logger.error(f"[ChatProcessor] Failed to finalize log and key stats for Official Key ID {official_key.id}. Error: {e}", exc_info=True)
            await db.rollback()

    async def non_stream_chat_completion(
        self, payload: Dict, upstream_format: ApiFormat, original_format: ApiFormat, model: str,
        official_key: str, global_rules: List, local_rules: List
    ) -> Tuple[Dict, int, ApiFormat]:
        target_url = f"{settings.GEMINI_BASE_URL}/v1beta/models/{model}:generateContent"
        headers = {"Content-Type": "application/json", "x-goog-api-key": official_key.key if hasattr(official_key, 'key') else official_key}
        
        response = await self.client.post(target_url, json=payload, headers=headers)
        
        if response.status_code != 200:
            converted_error = ErrorConverter.convert_upstream_error(response.content, response.status_code, upstream_format, original_format)
            return converted_error, response.status_code, original_format

        gemini_response = response.json()
        openai_response = universal_converter.gemini_response_to_openai_response(gemini_response, model)
        
        if openai_response.get('choices') and openai_response['choices'][0]['message'].get('content'):
            content = openai_response['choices'][0]['message']['content']
            content = self._apply_postprocessing(content, global_rules, local_rules)
            openai_response['choices'][0]['message']['content'] = content

        if original_format == "gemini":
            gemini_response = universal_converter.openai_response_to_gemini_response(openai_response)
            return gemini_response, 200, original_format
        
        return openai_response, 200, original_format

    async def _logged_stream_generator(self, generator: AsyncGenerator, db: AsyncSession, log_entry: Log, official_key: OfficialKey, start_time: float):
        ttft = 0.0
        first_chunk = True
        full_response_content = ""
        status_code = 200
        try:
            async for chunk in generator:
                if first_chunk:
                    ttft = time.time() - start_time
                    first_chunk = False
                
                if chunk.startswith(b'data: '):
                    content_part = chunk[6:].strip()
                    if content_part != b'[DONE]':
                        try:
                            json_content = json.loads(content_part)
                            chunks_to_process = json_content if isinstance(json_content, list) else [json_content]
                            for chunk_item in chunks_to_process:
                                if not isinstance(chunk_item, dict): continue

                                if chunk_item.get('error'):
                                    code = chunk_item.get('error', {}).get('code', 500)
                                    try:
                                        status_code = int(code)
                                    except (ValueError, TypeError):
                                        status_code = 500
                                if chunk_item.get('choices'):
                                    delta = chunk_item['choices'][0].get('delta', {})
                                    full_response_content += delta.get('content', '')
                        except json.JSONDecodeError:
                            pass
                yield chunk
        finally:
            latency = time.time() - start_time
            tokenizer = get_tokenizer(log_entry.model)
            output_tokens = len(tokenizer.encode(full_response_content))
            await self._finalize_log(db, log_entry, official_key, status_code, latency, output_tokens, ttft)


    async def stream_chat_completion(
        self, payload: Dict, upstream_format: ApiFormat, original_format: ApiFormat, model: str,
        official_key: str, global_rules: List, local_rules: List
    ) -> AsyncGenerator[bytes, None]:
        target_url = f"{settings.GEMINI_BASE_URL}/v1beta/models/{model}:streamGenerateContent"
        headers = {"Content-Type": "application/json", "x-goog-api-key": official_key.key if hasattr(official_key, 'key') else official_key}

        try:
            async with self.client.stream("POST", target_url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    error_content = await response.aread()
                    converted_error = ErrorConverter.convert_upstream_error(error_content, response.status_code, upstream_format, original_format)
                    yield f"data: {json.dumps(converted_error)}\n\n".encode()
                    return

                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    decoder = json.JSONDecoder()
                    while buffer:
                        buffer = buffer.lstrip(' \t\n\r,([')
                        if not buffer: break
                        try:
                            gemini_chunk, idx = decoder.raw_decode(buffer)
                            openai_chunk = universal_converter.gemini_to_openai_chunk(gemini_chunk, model)
                            if openai_chunk.get('choices') and openai_chunk['choices'][0]['delta'].get('content'):
                                content = openai_chunk['choices'][0]['delta']['content']
                                content = self._apply_postprocessing(content, global_rules, local_rules)
                                openai_chunk['choices'][0]['delta']['content'] = content
                            
                            if original_format == "gemini":
                                gemini_response_chunk = universal_converter.openai_chunk_to_gemini_chunk(openai_chunk)
                                yield f"data: {json.dumps(gemini_response_chunk)}\n\n".encode()
                            else:
                                yield f"data: {json.dumps(openai_chunk)}\n\n".encode()
                            
                            buffer = buffer[idx:]
                        except json.JSONDecodeError:
                            break
            yield b"data: [DONE]\n\n"
        except httpx.RequestError as e:
            logger.error(f"[ChatProcessor] Upstream request failed: {e}", exc_info=True)
            error_message = f"无法连接到上游服务: {type(e).__name__}"
            converted_error = ErrorConverter.convert_upstream_error(error_message.encode(), 502, "openai", original_format)
            yield f"data: {json.dumps(converted_error)}\n\n".encode()
            yield b"data: [DONE]\n\n"

chat_processor = ChatProcessor()
