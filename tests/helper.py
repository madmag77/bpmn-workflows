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
    config = {"configurable": {"thread_id": thread_id}}
    return app.invoke(
        input_kwargs,
        config,
        interrupt_after=interrupt_after,
    )
