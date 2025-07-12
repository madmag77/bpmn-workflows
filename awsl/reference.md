# AWsl Workflow Language

This folder contains an experimental workflow language named **AWsl**. The files here document the
syntax and execution requirements used by the accompanying parser and verifier.

## Requirements

### Core Assumptions
1. Runtime executes a directed acyclic graph extended with guarded loops (`cycle`) and human in the loop waits (`hitl`).
2. Nodes are external functions defined by name, inputs, outputs and a dictionary of immutable constants.
3. Long running `hitl` nodes suspend execution and produce a resumable snapshot.
4. Each workflow file describes exactly one runnable graph.
5. Data dependencies are inferred from declared inputs and outputs.
6. No shared mutable state. Nodes communicate only via immutable outputs.

### Functional Requirements
- **F1**: Single entry and exit nodes.
- **F2**: Conditional execution via `when { <boolean-expr> }` only.
- **F3**: `cycle` guarded loops and `parallel` blocks for concurrency.
- **F5**: Human in the loop suspension with the `hitl` clause.
- **F7**: Minimal type system: `Bool`, `Int`, `Float`, `String`, `File`, `Object<T>`, `List<T>`.
- **F8**: Implicit parameter validation at parse time.
- **F9**: Optional `metadata` blocks.
- **F10**: Per-node retry strategies with a `retry` clause.
- **F11**: Workflow level `inputs` and `outputs` declarations.
- **F12**: Optional per node `constants` dictionary.

### Execution Semantics
1. Node scheduling is determined from data dependencies.
2. `parallel` blocks run concurrently while preserving outer order.
3. `hitl` nodes emit resume tokens and persist workflow state.
4. All values are immutable.
5. Loop iterations run as independent sub graphs.
6. No runtime mutation of the graph is allowed.

## Keywords

`workflow`, `metadata`, `inputs`, `outputs`, `node`, `call`, `constants`, `when`,
`retry`, `backoff`, `policy`, `hitl`, `cycle`, `parallel`.

See `awsl.bnf` for the formal grammar definition.
