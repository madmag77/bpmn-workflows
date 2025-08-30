# Informal description
1. We use function identify_user_intent that returns enum of three values: qa, summarization, not_clear
2. We use condition function that depending on the previous output routes workflow to qa -> retrieve (with query param), summarize (with query param) -> generate, not_clear -> ask_user (with question parameter) 
3. Retrieve step returns the list of retrieved chunks
4. Generate returns answer param and it’s the end
5. After retrieve we have an evaluation step which returns relevance param - which is OK or BAD
6. after evaluation step we have conditional if OK routes to generate step and if BAD routes to rephrase step, if we do that for 3 times - route to generate with param error
7. Rephrase step takes query param and returns rephrased query param
8. After rephrase we go to retrieve again 


# Formal description
```
workflow IntentQA {
  parameters { }
  variables {
    rephraseCount: Int = 0
  }
  nodes {
    node identify_intent {
      type: FUNCTION
      action: "identify_user_intent"
      outputs {
        intent: Enum["qa","summarization","not_clear"]
      }
    }
    node ask_user {
      type: FUNCTION
      action: "ask_user"
      inputs {
        question: "Could you clarify your request?"
      }
      outputs {
        query: String
      }
    }
    node retrieve {
      type: FUNCTION
      action: "retrieve_financial_documents"
      inputs {
        query: from_query
      }
      outputs {
        chunks: List[String]
      }
    }
    node evaluate {
      type: FUNCTION
      action: "evaluate_relevance"
      inputs {
        chunks: chunks
      }
      outputs {
        relevance: Enum["OK","BAD"]
      }
    }
    node rephrase {
      type: FUNCTION
      action: "rephrase_query"
      inputs {
        query: from_query
      }
      outputs {
        new_query: String
      }
    }
    node summarize {
      type: FUNCTION
      action: "summarize"
      inputs {
        query: original_query
      }
      outputs {
        summary: String
      }
    }
    node generate {
      type: FUNCTION
      action: "generate_answer"
      inputs {
        source: result_source   ; either summary or chunks or error
      }
      outputs {
        answer: String
      }
    }
  }
  edges {
    edge { from: identify_intent; to: retrieve
           condition: intent == "qa"
           override: { from_query: identify_intent.input_text }
    }
    edge { from: identify_intent; to: summarize
           condition: intent == "summarization"
           override: { original_query: identify_intent.input_text }
    }
    edge { from: identify_intent; to: ask_user
           condition: intent == "not_clear"
    }
    edge { from: ask_user; to: retrieve
           override: { from_query: ask_user.query }
    }
    edge { from: retrieve; to: evaluate }
    edge { from: summarize; to: generate
           override: { result_source: summarize.summary }
    }
    edge { from: evaluate; to: generate
           condition: relevance == "OK"
           override: { result_source: evaluate.chunks }
    }
    edge { from: evaluate; to: rephrase
           condition: relevance == "BAD" && rephraseCount < 3
           update: { rephraseCount = rephraseCount + 1 }
           override: { from_query: retrieve.query }
    }
    edge { from: evaluate; to: generate
           condition: relevance == "BAD" && rephraseCount >= 3
           override: { result_source: "ERROR: no relevant chunks after retries" }
    }
    edge { from: rephrase; to: retrieve
           override: { from_query: rephrase.new_query }
    }
  }
  initial: identify_intent
  finals: [ generate ]
}
```
