import json
import os


def anthropic_to_openai_request(anthropic_data, target_model):
    req = {
        "model": target_model,
        "messages": [],
    }

    system_prompt = anthropic_data.get("system")
    if system_prompt:
        if isinstance(system_prompt, str):
            req["messages"].append({"role": "system", "content": system_prompt})
        elif isinstance(system_prompt, list):
            sys_text = "\n".join(
                b["text"] for b in system_prompt if b.get("type") == "text"
            )
            req["messages"].append({"role": "system", "content": sys_text})

    if "max_tokens" in anthropic_data:
        req["max_tokens"] = anthropic_data["max_tokens"]
    if "temperature" in anthropic_data:
        req["temperature"] = anthropic_data["temperature"]

    if "tools" in anthropic_data:
        req["tools"] = []
        for t in anthropic_data["tools"]:
            req["tools"].append(
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": t.get("input_schema", {}),
                    },
                }
            )

    for msg in anthropic_data.get("messages", []):
        role = msg["role"]
        content = msg["content"]

        if isinstance(content, str):
            req["messages"].append({"role": role, "content": content})
            continue

        text_content = ""
        tool_calls = []

        for block in content:
            if block["type"] == "text":
                text_content += block["text"]
            elif block["type"] == "tool_use":
                tool_calls.append(
                    {
                        "id": block["id"],
                        "type": "function",
                        "function": {
                            "name": block["name"],
                            "arguments": json.dumps(block["input"]),
                        },
                    }
                )
            elif block["type"] == "tool_result":
                tool_msg = {
                    "role": "tool",
                    "tool_call_id": block["tool_use_id"],
                    "content": "",
                }
                if isinstance(block.get("content"), str):
                    tool_msg["content"] = block["content"]
                elif isinstance(block.get("content"), list):
                    texts = [b["text"] for b in block["content"] if b["type"] == "text"]
                    tool_msg["content"] = "\n".join(texts)
                req["messages"].append(tool_msg)

        if role == "assistant":
            ast_msg = {"role": "assistant"}
            if text_content:
                ast_msg["content"] = text_content
            else:
                ast_msg["content"] = ""
            if tool_calls:
                ast_msg["tool_calls"] = tool_calls
            req["messages"].append(ast_msg)
        elif role == "user":
            if text_content:
                req["messages"].append({"role": "user", "content": text_content})

    # Zhipu/GLM/Mistral Safety Patch: ensure assistant content is never fully null if required by strict APIs
    for m in req.get("messages", []):
        if m.get("role") == "assistant" and "content" not in m:
            m["content"] = ""
        if isinstance(m.get("content"), list):
            m["content"] = "\n".join([str(item) for item in m["content"]])

    return req


def openai_to_anthropic_response(resp, original_model):
    if not resp.get("choices"):
        return resp

    choice = resp["choices"][0]
    msg = choice.get("message", {})

    anthropic_content = []
    if msg.get("content"):
        anthropic_content.append({"type": "text", "text": msg["content"]})

    if msg.get("tool_calls"):
        for tc in msg["tool_calls"]:
            anthropic_content.append(
                {
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "input": json.loads(tc["function"]["arguments"])
                    if tc["function"].get("arguments")
                    else {},
                }
            )

    finish_reason = choice.get("finish_reason")
    stop_reason = "end_turn"
    if finish_reason == "tool_calls":
        stop_reason = "tool_use"
    elif finish_reason == "length":
        stop_reason = "max_tokens"

    return {
        "id": "msg_proxy_" + resp.get("id", os.urandom(4).hex()),
        "type": "message",
        "role": "assistant",
        "model": original_model,
        "content": anthropic_content,
        "stop_reason": stop_reason,
        "usage": {
            "input_tokens": resp.get("usage", {}).get("prompt_tokens", 0),
            "output_tokens": resp.get("usage", {}).get("completion_tokens", 0),
        },
    }


def handle_openai_stream(handler, response, original_model, is_anthropic):
    """
    Robust translation stream that reads chunked HTTP data from the provider
    and safely streams Anthropic SSE events back to the client.
    Includes connection recovery and safety disconnect catching.
    """
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "keep-alive")
    handler.end_headers()

    if not is_anthropic:
        # If client expects raw OpenAI stream, just pipe it through
        try:
            for line in response.iter_lines():
                if line:
                    handler.wfile.write(line + b"\n")
                    handler.wfile.flush()
        except Exception as e:
            print(f"[Proxy Stream Warning] Upstream disconnected early: {e}")
        return

    msg_id = "msg_proxy_" + os.urandom(4).hex()

    start_event = {
        "type": "message_start",
        "message": {
            "id": msg_id,
            "type": "message",
            "role": "assistant",
            "content": [],
            "model": original_model,
            "stop_reason": None,
            "stop_sequence": None,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        },
    }
    handler.wfile.write(
        f"event: message_start\ndata: {json.dumps(start_event)}\n\n".encode()
    )

    current_block_index = -1
    in_text_block = False
    active_tools = {}
    sent_stop = False

    try:
        for line in response.iter_lines():
            if not line:
                continue
            line = line.decode("utf-8", errors="ignore").strip()
            if not line or not line.startswith("data: "):
                continue

            data_str = line[6:]
            if data_str == "[DONE]":
                break

            try:
                chunk = json.loads(data_str)
            except:
                continue

            if not chunk.get("choices"):
                continue

            delta = chunk["choices"][0].get("delta", {})
            finish_reason = chunk["choices"][0].get("finish_reason")

            if "content" in delta and delta["content"] is not None:
                content = delta["content"]
                if not in_text_block:
                    current_block_index += 1
                    in_text_block = True
                    t_start = {
                        "type": "content_block_start",
                        "index": current_block_index,
                        "content_block": {"type": "text", "text": ""},
                    }
                    handler.wfile.write(
                        f"event: content_block_start\ndata: {json.dumps(t_start)}\n\n".encode()
                    )

                t_delta = {
                    "type": "content_block_delta",
                    "index": current_block_index,
                    "delta": {"type": "text_delta", "text": content},
                }
                handler.wfile.write(
                    f"event: content_block_delta\ndata: {json.dumps(t_delta)}\n\n".encode()
                )
                handler.wfile.flush()

            if "tool_calls" in delta:
                if in_text_block:
                    in_text_block = False
                    t_stop = {
                        "type": "content_block_stop",
                        "index": current_block_index,
                    }
                    handler.wfile.write(
                        f"event: content_block_stop\ndata: {json.dumps(t_stop)}\n\n".encode()
                    )

                for tc in delta["tool_calls"]:
                    tc_index = tc["index"]
                    if tc_index not in active_tools:
                        current_block_index += 1
                        active_tools[tc_index] = current_block_index

                        t_id = tc.get("id", "call_" + os.urandom(4).hex())
                        t_name = tc.get("function", {}).get("name", "unknown")

                        tl_start = {
                            "type": "content_block_start",
                            "index": current_block_index,
                            "content_block": {
                                "type": "tool_use",
                                "id": t_id,
                                "name": t_name,
                                "input": {},
                            },
                        }
                        handler.wfile.write(
                            f"event: content_block_start\ndata: {json.dumps(tl_start)}\n\n".encode()
                        )

                    if "function" in tc and "arguments" in tc["function"]:
                        args_str = tc["function"]["arguments"]
                        if args_str:
                            tl_delta = {
                                "type": "content_block_delta",
                                "index": active_tools[tc_index],
                                "delta": {
                                    "type": "input_json_delta",
                                    "partial_json": args_str,
                                },
                            }
                            handler.wfile.write(
                                f"event: content_block_delta\ndata: {json.dumps(tl_delta)}\n\n".encode()
                            )
                            handler.wfile.flush()

            if finish_reason:
                if in_text_block:
                    t_stop = {
                        "type": "content_block_stop",
                        "index": current_block_index,
                    }
                    handler.wfile.write(
                        f"event: content_block_stop\ndata: {json.dumps(t_stop)}\n\n".encode()
                    )
                    in_text_block = False

                for tc_index in active_tools:
                    tl_stop = {
                        "type": "content_block_stop",
                        "index": active_tools[tc_index],
                    }
                    handler.wfile.write(
                        f"event: content_block_stop\ndata: {json.dumps(tl_stop)}\n\n".encode()
                    )

                stop_reason_str = "end_turn"
                if finish_reason == "tool_calls":
                    stop_reason_str = "tool_use"
                elif finish_reason == "length":
                    stop_reason_str = "max_tokens"

                m_delta = {
                    "type": "message_delta",
                    "delta": {"stop_reason": stop_reason_str, "stop_sequence": None},
                    "usage": {"output_tokens": 0},
                }
                handler.wfile.write(
                    f"event: message_delta\ndata: {json.dumps(m_delta)}\n\n".encode()
                )
                handler.wfile.write(
                    b'event: message_stop\ndata: {"type": "message_stop"}\n\n'
                )
                handler.wfile.flush()
                sent_stop = True
                break
    except Exception as stream_err:
        print(f"[Proxy Stream Warning] Upstream disconnected early: {stream_err}")

    if not sent_stop:
        if in_text_block:
            t_stop = {"type": "content_block_stop", "index": current_block_index}
            handler.wfile.write(
                f"event: content_block_stop\ndata: {json.dumps(t_stop)}\n\n".encode()
            )

        for tc_index in active_tools:
            tl_stop = {"type": "content_block_stop", "index": active_tools[tc_index]}
            handler.wfile.write(
                f"event: content_block_stop\ndata: {json.dumps(tl_stop)}\n\n".encode()
            )

        m_delta = {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn", "stop_sequence": None},
            "usage": {"output_tokens": 0},
        }
        handler.wfile.write(
            f"event: message_delta\ndata: {json.dumps(m_delta)}\n\n".encode()
        )
        handler.wfile.write(b'event: message_stop\ndata: {"type": "message_stop"}\n\n')
        handler.wfile.flush()
