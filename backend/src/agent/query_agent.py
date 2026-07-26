import os
import json
import asyncio
from openai import OpenAI
from src.agent.sar_generator import generate_sar as run_generate_sar

def get_llm_client():
    api_key = os.environ.get("GROK_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("API KEY environment variable is missing.")
        
    if api_key.startswith("gsk_"):
        base_url = "https://api.groq.com/openai/v1"
        model_name = "llama-3.3-70b-versatile"
    elif os.environ.get("GROK_API_KEY") and not api_key.startswith("sk-"):
        base_url = "https://api.x.ai/v1"
        model_name = "grok-beta"
    else:
        base_url = None
        model_name = "gpt-4o-mini"
        
    return OpenAI(api_key=api_key, base_url=base_url), model_name

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_top_high_risk_customers",
            "description": "Get a list of the top N highest risk customers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "string",
                        "description": "Number of customers to return. Default 5, max 20. Provide as a string (e.g. '5')."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_profile",
            "description": "Get detailed profile information and risk evaluation for a specific customer ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "The exact customer ID, e.g. CUST_00707"
                    }
                },
                "required": ["customer_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_dataset_statistics",
            "description": "Get overall statistics for the transaction dataset.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_sar",
            "description": "Generate a formal Suspicious Activity Report (SAR) or Risk Assessment for a customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "The exact customer ID to generate the report for."
                    }
                },
                "required": ["customer_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_transactions",
            "description": "Get raw transaction history for a specific customer, showing mode of payment (channel), amounts, and timestamps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "The exact customer ID, e.g. CUST_00707"
                    },
                    "limit": {
                        "type": "string",
                        "description": "Max number of recent transactions to return. Default is '10'. Provide as string."
                    }
                },
                "required": ["customer_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_transactions_dataframe",
            "description": "Execute a Python Pandas expression against the entire raw transactions dataset to answer arbitrary statistical or search questions. The dataframe is available as 'df'. Example expressions: 'df.sort_values(\"amount\", ascending=False).head(1).to_dict(orient=\"records\")' or 'df[\"channel\"].value_counts().to_dict()'. Return a dict or list.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pandas_expression": {
                        "type": "string",
                        "description": "A valid Pandas python expression that evaluates to a result. Use 'df' as the dataframe variable."
                    }
                },
                "required": ["pandas_expression"]
            }
        }
    }
]

def execute_tool(app_state, name: str, args: dict):
    if name == "get_top_high_risk_customers":
        try:
            limit = int(args.get("limit", 5))
        except (ValueError, TypeError):
            limit = 5
        limit = min(limit, 20)
        risk_df = getattr(app_state, "risk_summary_df", None)
        if risk_df is None or risk_df.empty:
            return {"error": "No risk data available."}
        
        high_risk_df = risk_df[risk_df["risk_level"] == "high"].sort_values("final_score", ascending=False)
        top_n = high_risk_df.head(limit)
        return top_n[["customer_id", "risk_level", "final_score", "triggered_rules"]].to_dict(orient="records")

    elif name == "get_customer_profile":
        customer_id = args.get("customer_id")
        risk_df = getattr(app_state, "risk_summary_df", None)
        if risk_df is None or risk_df.empty:
            return {"error": "No risk data available."}
        
        cust_df = risk_df[risk_df["customer_id"] == customer_id]
        if cust_df.empty:
            return {"error": f"Customer {customer_id} not found."}
        
        return cust_df.iloc[0].to_dict()

    elif name == "get_dataset_statistics":
        risk_df = getattr(app_state, "risk_summary_df", None)
        if risk_df is None or risk_df.empty:
            return {"error": "No risk data available."}
            
        stats = {
            "total_customers_scored": len(risk_df),
            "risk_levels": risk_df["risk_level"].value_counts().to_dict(),
            "average_score": risk_df["final_score"].mean(),
            "max_score": risk_df["final_score"].max()
        }
        return stats

    elif name == "generate_sar":
        customer_id = args.get("customer_id")
        risk_df = getattr(app_state, "risk_summary_df", None)
        if risk_df is None or risk_df.empty:
            return {"error": "No risk data available."}
        
        cust_df = risk_df[risk_df["customer_id"] == customer_id]
        if cust_df.empty:
            return {"error": f"Customer {customer_id} not found."}
            
        profile = cust_df.iloc[0].to_dict()
        try:
            report = run_generate_sar(profile)
            return {"report": report}
        except Exception as e:
            return {"error": str(e)}

    elif name == "get_customer_transactions":
        customer_id = args.get("customer_id")
        try:
            limit = int(args.get("limit", 10))
        except (ValueError, TypeError):
            limit = 10
        df = getattr(app_state, "transactions_df", None)
        if df is None or df.empty:
            return {"error": "No transaction data available."}
            
        cust_txns = df[df["customer_id"] == customer_id]
        if cust_txns.empty:
            return {"error": f"No transactions found for customer {customer_id}."}
            
        import pandas as pd
        recent = cust_txns.sort_values("timestamp", ascending=False).head(limit)
        # Convert timestamp to string for JSON serialization
        recent = recent.copy()
        recent["timestamp"] = recent["timestamp"].astype(str)
        recent = recent.where(pd.notnull(recent), None)
        return recent.to_dict(orient="records")

    elif name == "analyze_transactions_dataframe":
        expression = args.get("pandas_expression")
        df = getattr(app_state, "transactions_df", None)
        if df is None or df.empty:
            return {"error": "No transaction data available."}
            
        try:
            # Safely evaluate the expression with access to 'df' and 'pd'
            import pandas as pd
            local_env = {"df": df, "pd": pd}
            result = eval(expression, {"__builtins__": {}}, local_env)
            
            # Convert pandas types to standard python types for JSON
            if isinstance(result, pd.DataFrame):
                result = result.where(pd.notnull(result), None)
                return result.to_dict(orient="records")
            elif isinstance(result, pd.Series):
                result = result.where(pd.notnull(result), None)
                return result.to_dict()
            elif isinstance(result, list):
                return result
            elif hasattr(result, "item"): # numpy scalar
                return {"result": result.item()}
            else:
                return {"result": result}
        except Exception as e:
            return {"error": f"Failed to execute expression: {str(e)}"}

    return {"error": f"Unknown tool {name}"}

async def run_agent_query(request_messages: list, app_state):
    # Get the latest user query string for intent event
    latest_query = request_messages[-1].content if request_messages else ""

    try:
        client, model_name = get_llm_client()
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'data': {'message': f'Failed to initialize AI: {str(e)}'}})}\n\n"
        return

    # Yield intent detected
    yield f"data: {json.dumps({'type': 'intent_detected', 'data': {'query': latest_query}})}\n\n"
    await asyncio.sleep(0.1)

    system_message = {
        "role": "system",
        "content": (
            "You are Limier, an expert AML (Anti-Money Laundering) AI assistant. "
            "Use the provided tools to query the dataset. Remember context from the conversation history.\n\n"
            "CRITICAL GROUNDING RULE: Every claim you make about a specific transaction amount, date, counterparty, or channel "
            "MUST cite the real transaction_id from the dataset (e.g. 'TXN_6f4bab25d6'). "
            "Never state specific amounts or dates without the supporting transaction ID. "
            "If you don't have the transaction ID, say so instead of guessing.\n\n"
            "When executing pandas expressions, the dataframe is named 'df' with columns: "
            "'transaction_id', 'customer_id', 'amount', 'timestamp', 'channel', 'direction', "
            "'counterparty_id', 'counterparty_country', 'transaction_type', 'is_planted_suspicious', 'planted_pattern'.\n\n"
            "SAR FORMAT: If generating a SAR, YOU MUST return it formatted in MARKDOWN with this EXACT structure:\n\n"
            "## Suspicious Activity Report\n"
            "**Customer / Account:** [ID]\n"
            "**Risk Score:** [Score] / 100 | **Risk Level:** [HIGH/MEDIUM/LOW]\n"
            "**Date Range:** [Dates from dataset]\n\n"
            "### Triggered Rules\n"
            "- [Rule name]: [One-line description]\n\n"
            "### Key Contributing Factors (SHAP)\n"
            "| Feature | Value | SHAP Contribution |\n"
            "|---------|-------|------------------|\n"
            "| [feature] | [value] | [+/-X.XXX] |\n\n"
            "### Evidence Transactions\n"
            "| TXN ID | Date | Amount | Channel | Direction |\n"
            "|--------|------|--------|---------|----------|\n"
            "| [real TXN ID] | [date] | $[amount] | [channel] | [credit/debit] |\n\n"
            "### Narrative Summary\n"
            "[2-3 plain English paragraphs explaining WHY this is suspicious, citing specific TXN IDs.]\n\n"
            "Always use real data from tool calls — never fabricate transaction IDs, amounts, or dates."
        )
    }

    # request_messages contains Pydantic MessageItem models, convert to dicts
    history = [{"role": msg.role, "content": msg.content} for msg in request_messages]
    
    messages = [system_message] + history

    max_loops = 5
    loop_count = 0

    while loop_count < max_loops:
        loop_count += 1
        
        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=0.1
                )
            )
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': f'LLM API Error: {str(e)}'}})}\n\n"
            break

        message = response.choices[0].message
        
        # Convert message to dict to avoid serialization issues on next request
        msg_dict = {"role": message.role, "content": message.content}
        if message.tool_calls:
            msg_dict["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                }
                for tc in message.tool_calls
            ]
        messages.append(msg_dict)

        if message.tool_calls:
            for tool_call in message.tool_calls:
                name = tool_call.function.name
                
                try:
                    args = json.loads(tool_call.function.arguments)
                except Exception:
                    args = {}
                
                yield f"data: {json.dumps({'type': 'tool_call', 'data': {'tool': name, 'arguments': args}})}\n\n"
                
                # Execute tool locally
                try:
                    result = await loop.run_in_executor(None, lambda: execute_tool(app_state, name, args))
                except Exception as e:
                    result = {"error": str(e)}
                    
                yield f"data: {json.dumps({'type': 'tool_result', 'data': {'tool': name, 'result': result}}, default=str)}\n\n"
                
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": name,
                    "content": json.dumps(result, default=str)
                })
        else:
            # We got a final text answer
            final_text = message.content or ""
            # Identify any flagged items for the UI if a tool call was made
            flagged_items = []
            for m in messages:
                if m.get("role") == "tool" and m.get("name") in ["get_top_high_risk_customers", "get_customer_profile"]:
                    try:
                        res = json.loads(m["content"])
                        if isinstance(res, list):
                            flagged_items.extend(res)
                        elif isinstance(res, dict) and "customer_id" in res:
                            flagged_items.append(res)
                    except:
                        pass
                        
            yield f"data: {json.dumps({'type': 'final_answer', 'data': {'text': final_text, 'flagged_items': flagged_items}})}\n\n"
            break

    if loop_count >= max_loops:
        yield f"data: {json.dumps({'type': 'error', 'data': {'message': 'Agent iteration limit exceeded.'}})}\n\n"
