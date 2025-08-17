# The tasks not to forget about

## Tasks

1. In AWSL workflows when loading it checks that for each node all inputs from `when` are in `inputs`.
2. `call` instruction now is somewhat special so it should be first in the node definition, I think it's wrong, it can be anywhere, it's just the same element as inputs and outputs.
3. Workflow functions (that we mention in `call`) shouldn't have access to the whole state of the workflow, we need to pass to them only inputs defined in their inputs block, and also we need to remove node name from inputs, if in the inputs there is `String input1 = previousNode.output1` we need to pass internal name `input1` so node function can work independently from other parts of the workflow.
4. We need to return from workflow only what was mentioned in it's output.
5. We need to verify that there is no uncontrolled cycles in the graph (no nodes directly or indirectly mutually dependent). All cycles should be implemented using special `cycle` block.

## Think about

1. Can we make syntax inside nodes linked and that sounds more like a natural sentence? something like `given the inputs, call the function, when conditions are met and return the following outputs`.
2. Is there a way to describe all the semantic checks we want the awsl workflow to follow in a non-code way? for instance, that there should be at least one `call` in a node, at least one `node` in a workflow, that all inputs from `when` should be in `inputs`, that node shouldn't depend on non-existing inputs, and so on. BNF grammar helps to check syntax but not all semantic rules.

## Workflows I'd like to create first

1. Workflow that iterate through files (pdf) with papers in a specific folder (like papers_sink), for each paper it should parse it (VLLM) extract paper title, year, couple of first authors, generate proper name (2025-title-authors) and move the file to another folder (like papers_to_read). I download papers to sink folder with their weird names and every day (or hour?) they will be renamed and moved to a proper place.
2. I'd like another workflow at 5am everyday scrape the news from the list of resources I provide and prepare a summary for me. Resources, like OpenAI, Anthropic, etc blogs, Karpathy blog, etc. It should understand, where it stopped last time so provide only new articles and posts. The resul should be saved in my notes in Obsidian.
