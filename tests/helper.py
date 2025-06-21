import run_bpmn_workflow as runner
import workflow_functions as wf

def run_workflow(xml_path: str, fn_overrides=None, params=None):
    fn_map = {name: getattr(wf, name) for name in dir(wf) if not name.startswith("_")}
    if fn_overrides:
        fn_map.update(fn_overrides)
    app = runner.build_graph(xml_path, functions=fn_map)
    input_kwargs = {"input_text": "hello", "rephraseCount": 0}
    if params:
        input_kwargs.update(params)
    return app.invoke(input_kwargs)
