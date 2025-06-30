from bpmn_workflows.run_bpmn_workflow import run_workflow
import steps.deepresearch_functions as drf
import chainlit as cl
from chainlit import make_async, AskUserMessage
import os
import json
import uuid
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.memory import MemorySaver

DATABASE_URL = os.getenv("DATABASE_URL","")
if DATABASE_URL == "":
    raise ValueError("DATABASE_URL is not set")
if DATABASE_URL:
    _saver_cm = PostgresSaver.from_conn_string(DATABASE_URL)
    CHECKPOINTER = _saver_cm.__enter__()
    CHECKPOINTER.setup()
else:
    CHECKPOINTER = MemorySaver()

XML_PATH = "workflows/deepresearch/deepresearch.xml"
FN_MAP = {name: getattr(drf, name) for name in dir(drf) if not name.startswith("_")}

@cl.on_app_shutdown
async def shutdown():
    if DATABASE_URL:
        _saver_cm.__exit__(None, None, None)

@cl.on_chat_start
async def main():
    await cl.Message(content="I'm a DeepResearch agent. How can I help you today?").send()
    
@cl.on_message
async def handle_message(message: cl.Message):
    """Run deepresearch workflow when a user sends a message."""
    try:
        # Show a loading message
        msg = cl.Message(content="Processing your request... This may take a few minutes.")
        await msg.send()

        thread_id = cl.user_session.get("thread_id")
        if not thread_id:
            thread_id = str(uuid.uuid4())
            cl.user_session.set("thread_id", thread_id)

        result = await make_async(run_workflow)(
            XML_PATH,
            fn_map=FN_MAP,
            params={"query": message.content},
            thread_id=thread_id,
            checkpointer=CHECKPOINTER,
        )

        while "__interrupt__" in result:
            intr = result["__interrupt__"][0]
            questions = "\n".join(intr.value.get("questions", []))
            user_res = await AskUserMessage(content=questions).send()
            result = await make_async(run_workflow)(
                XML_PATH,
                fn_map=FN_MAP,
                thread_id=thread_id,
                checkpointer=CHECKPOINTER,
                resume=json.dumps(user_res.output),
            )
        
        answer = result.get("final_answer") or ""
        await cl.Message(content=answer).send()
    except Exception as exc:
        await cl.Message(content=f"Error: {exc}").send()