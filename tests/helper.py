import run_bpmn_workflow as runner
import steps.example_functions as wf

def run_workflow(
    xml_path: str,
    fn_overrides=None,
    params=None,
    *,
    checkpointer=None,
    thread_id="test",
    interrupt_after=None,
    recursion_limit=100,
    resume=None,
):
    fn_map = {
        name: getattr(wf, name)
        for name in dir(wf)
        if not name.startswith("_")
    }
    if fn_overrides:
        fn_map.update(fn_overrides)
    app = runner.build_graph(xml_path, functions=fn_map, checkpointer=checkpointer)
    input_kwargs = {"input_text": "hello", "rephraseCount": 0}
    if params:
        input_kwargs.update(params)
    if resume is not None:
        from langgraph.types import Command
        invoke_obj = Command(resume=resume)
    else:
        invoke_obj = input_kwargs
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": recursion_limit}
    return app.invoke(
        invoke_obj,
        config,
        interrupt_after=interrupt_after,
    )
