# Requirements

Step 1 – Core Assumptions
 1. Runtime executes an explicit Directed Acyclic Graph extended with guarded loops (cycle) and waits (hitl); the DSL compiles into that representation.
 2. Nodes are external functions (language-agnostic) exposing name, inputs, outputs, and an immutable constants dictionary; they contain no internal logic.
 3. Long-running human/agent wait nodes suspend execution and produce a resumable state snapshot.
 4. One workflow file ⇒ one runnable graph. (Versioning/namespacing deferred.)
 5. Data-dependency edges are implicit: a node becomes eligible when all its declared inputs are available; no explicit edge syntax.
 6. No shared mutable state: workflows rely solely on message passing via immutable outputs; global context is forbidden.

⸻

Step 2 – Functional Requirements

ID Requirement
F1 Single entry & exit: exactly one entry node and one exit node; every path must reach the exit.
F2 when-only branching: conditional execution via `when { <boolean-expr> }`; no other branching constructs.
F3 Loops & parallelism:

- Guarded loop with `cycle` keyword (when { … }), with guard { … } exit and max_iterations.
- Parallel execution with `parallel` of N block spins up N concurrent sub-graphs; join policy is always “all” and outputs as a `List<T>`.
F5 Human-In-The-Loop: `hitl { correlation: <string>, timeout: <duration> }` on nodes suspends and awaits external resume token.
F7 Strong minimal type system: `Bool, Int, Float, String, File, Object<…>, List<T>`.
F8 Implicit parameter validation at parse-time: missing input, unused output, or type mismatch must be detected.
F9 Metadata: each workflow or node may include a `metadata { description: <string>; owner: <string>; version: <string> }` block (ignored by engine).
F10 Error-handling (retry): per-node `retry { attempts: <int>; backoff: <strategy>; policy: <fail_policy> }`; no catch or finally.
F11 Workflow interface: top-level inputs { … } and outputs { … } blocks declare the workflow’s public parameters.
F12 Constants: each node may contain a `constants { <key>: <literal>; … }` dictionary for arbitrary, immutable parameters.

⸻

Step 3 – Execution-Semantics Requirements
 1. Engine derives the ready-to-run set by implicit data-dependency analysis; scheduling order is otherwise undefined.
 2. Parallel blocks map to concurrent execution units; outer sequence order is preserved.
 3. On HITL nodes the engine emits a callback/outbox event and persists state; resumption requires the external token.
 4. All values are immutable; outputs become read-only inputs downstream.
 5. Loop iterations execute as separate sub-graphs; engine may cap concurrency.
 6. The graph remains acyclic at runtime; no mutation of shared context occurs.

## **1. Keywords & Types**

| **Keyword**   | **Category** | **Purpose**                                                                                    |
| ------------- | ------------ | ---------------------------------------------------------------------------------------------- |
| **workflow**  | block        | Defines a named workflow                                                                       |
| **metadata**  | block        | Arbitrary workflow- or node-level metadata (description, owner, version)                       |
| **inputs**    | block        | Declares workflow- or node-level inputs                                                        |
| **outputs**   | block        | Declares workflow- or node-level outputs                                                       |
| **node**      | block        | Declares an atomic execution step (external function)                                          |
| **call**      | statement    | Names the external function to execute                                                         |
| **constants** | block        | Node-local arbitrary immutable parameters                                                      |
| **when**      | guard        | Conditional execution guard for nodes or loops                                                 |
| **retry**     | clause       | Per-node retry strategy on failure                                                             |
| **backoff**   | modifier     | Delay strategy inside a retry                                                                  |
| **policy**    | modifier     | Failure policy (on retry or cycle)                                                             |
| **hitl**      | clause       | Human-or-agent wait configuration                                                              |
| **cycle**     | block        | Guarded loop construct, optionally with inner parallel                                         |
| **parallel**  | block        | Special construct specifies N copies of its sub-workflow to run concurrently; joins with “all” |

### **Types**

|**Type**|**Description**|
|---|---|
|**Bool**|Boolean|
|**Int**|Integer|
|**Float**|Floating-point number|
|**String**|Text string|
|**File**|File handle/reference|
|**Object**|Structured object of type T|
|**List**|Sequence of elements of type T|
