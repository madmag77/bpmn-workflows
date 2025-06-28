from bpmn_workflows.run_bpmn_workflow import run_workflow
import steps.deepresearch_functions as drf
import chainlit as cl

XML_PATH = "workflows/deepresearch/deepresearch.xml"
FN_MAP = {name: getattr(drf, name) for name in dir(drf) if not name.startswith("_")}

@cl.on_chat_start
async def main():
    await cl.Message(content="I'm a DeepResearch agent. How can I help you today?").send()
    
@cl.on_message
async def handle_message(message: cl.Message):
    """Run deepresearch workflow when a user sends a message."""
    try:
        result = run_workflow(XML_PATH, fn_map=FN_MAP, params={"query": message.content})
        answer = result.get("final_answer") or ""
        await cl.Message(content=answer).send()
    except Exception as exc:
        await cl.Message(content=f"Error: {exc}").send()