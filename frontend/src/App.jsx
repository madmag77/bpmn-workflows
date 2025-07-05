import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import './App.css'
import { continueWorkflow as apiContinue, startWorkflow as apiStart, getWorkflow, getWorkflows, getWorkflowTemplates } from './api.js'
import { cancelWorkflow as apiCancel } from './api.js'
import { POLL_INTERVAL_MS } from './constants.js'
import { startPolling } from './timer.js'

export default function App() {
  const [workflows, setWorkflows] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [selected, setSelected] = useState(null)
  const [showInterrupt, setShowInterrupt] = useState(false)
  const [expandedSections, setExpandedSections] = useState({})
  const [templates, setTemplates] = useState([])
  const [showStartModal, setShowStartModal] = useState(false)
  const [newTemplate, setNewTemplate] = useState('')
  const [newQuery, setNewQuery] = useState('')

  useEffect(() => {
    const fetchList = () => {
      getWorkflows().then(data => {
        setWorkflows(data)
        setSelectedId(current => {
          if (current === null && data.length > 0) {
            return data[0].id
          }
          return current
        })
      })
    }

    fetchList()
    const id = startPolling(fetchList, POLL_INTERVAL_MS)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    getWorkflowTemplates().then(data => {
      setTemplates(data)
      if (data.length > 0) {
        setNewTemplate(data[0].id)
      }
    })
  }, [])

  useEffect(() => {
    if (!selectedId) return

    getWorkflow(selectedId).then(setSelected)
  }, [selectedId])

  useEffect(() => {
    if (!selectedId || selected?.status !== 'running') return

    const fetchSelected = () => {
      getWorkflow(selectedId).then(setSelected)
    }

    const id = startPolling(fetchSelected, POLL_INTERVAL_MS)
    return () => clearInterval(id)
  }, [selectedId, selected?.status])

  useEffect(() => {
    if (selected && selected.status === 'needs_input' && selected.result?.__interrupt__) {
      setShowInterrupt(true)
    } else {
      setShowInterrupt(false)
    }
  }, [selected])

  const openStartModal = () => {
    setNewQuery('')
    if (templates.length > 0) {
      setNewTemplate(templates[0].id)
    }
    setShowStartModal(true)
  }

  const confirmStartWorkflow = async () => {
    setShowStartModal(false)
    const data = await apiStart(newTemplate, newQuery)
    setWorkflows([...workflows, { id: data.id, template: newTemplate, status: data.status }])
    setSelectedId(data.id)
    setSelected(data)
  }

  const cancelStartWorkflow = () => {
    setShowStartModal(false)
  }

  const continueWorkflow = async answer => {
    const data = await apiContinue(selectedId, answer)
    setWorkflows(workflows.map(w => (w.id === selectedId ? { ...w, status: data.status } : w)))
    setSelected(data)
    setShowInterrupt(false)
  }

  const cancelRunningWorkflow = async () => {
    const data = await apiCancel(selectedId)
    setWorkflows(workflows.map(w => (w.id === selectedId ? { ...w, status: data.status } : w)))
    setSelected(data)
  }

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }))
  }

  const [answer, setAnswer] = useState('')
  const interrupt = selected?.result?.__interrupt__?.[0]

  // Extract key information from the result
  const extractWorkflowInfo = (result) => {
    if (!result) return null

    const query = result.query || ''
    const finalAnswer = result.final_answer || ''
    const extendedQuery = result.extended_query || ''
    const questions = result.questions || []
    const clarifications = result.clarifications || {}
    const chunks = result.chunks || []
    const researchIteration = result.ResearchLoop_iteration || 0
    const iteration = result.iteration || 0

    return {
      query,
      finalAnswer,
      extendedQuery,
      questions,
      clarifications,
      chunks,
      researchIteration,
      iteration,
      rawResult: result
    }
  }

  const workflowInfo = selected ? extractWorkflowInfo(selected.result) : null

  return (
    <div className="container">
      <aside className="sidebar">
        <h2>Workflows</h2>
        <ul className="workflow-list">
          {workflows.map(w => (
            <li
              key={w.id}
              onClick={() => setSelectedId(w.id)}
              className={w.id === selectedId ? 'selected' : ''}
            >
              <span className="title">{w.template}</span>
              <span className={`state state-${w.status.replace(/[\s_]+/g, '-').toLowerCase()}`}>{w.status}</span>
            </li>
          ))}
        </ul>
        <button className="new-workflow" onClick={openStartModal}>Start New Workflow</button>
      </aside>
      <main className="content">
        {selected ? (
          <>
            <div className="workflow-header">
              <h2>{selected.template}</h2>
              <span className={`status-badge status-${selected.status.replace(/[\s_]+/g, '-').toLowerCase()}`}>
                {selected.status}
              </span>
              {selected.status === 'running' && (
                <button className="cancel-btn" onClick={cancelRunningWorkflow}>Cancel Workflow</button>
              )}
            </div>

            {showInterrupt && interrupt ? (
              <div className="interrupt-section">
                <h3>🤔 Questions</h3>
                <div className="questions-list">
                  {interrupt.value.questions.map((question, idx) => (
                    <p key={idx} className="question">{question}</p>
                  ))}
                </div>
                <div className="answer-input">
                  <input
                    value={answer}
                    onChange={e => setAnswer(e.target.value)}
                    placeholder="Enter your answer..."
                    className="answer-field"
                  />
                  <button
                    onClick={() => { continueWorkflow(answer); setAnswer(''); }}
                    className="continue-btn"
                  >
                    Continue
                  </button>
                  <button
                    onClick={() => { setShowInterrupt(false); setAnswer(''); }}
                    className="cancel-btn"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : workflowInfo ? (
              <div className="workflow-result">
                {/* Initial Query */}
                <div className="result-section">
                  <h3>🎯 Initial Query</h3>
                  <div className="query-box">
                    <ReactMarkdown>{workflowInfo.query}</ReactMarkdown>
                  </div>
                </div>

                {/* Final Answer */}
                {workflowInfo.finalAnswer && (
                  <div className="result-section">
                    <h3>✅ Final Answer</h3>
                    <div className="final-answer">
                      <ReactMarkdown>{workflowInfo.finalAnswer}</ReactMarkdown>
                    </div>
                  </div>
                )}

                {/* Extended Query */}
                {workflowInfo.extendedQuery && (
                  <div className="result-section">
                    <div
                      className="section-header"
                      onClick={() => toggleSection('extended')}
                    >
                      <h3>🔍 Extended Query</h3>
                      <span className="toggle-icon">
                        {expandedSections.extended ? '▼' : '▶'}
                      </span>
                    </div>
                    {expandedSections.extended && (
                      <div className="section-content">
                        <ReactMarkdown>{workflowInfo.extendedQuery}</ReactMarkdown>
                      </div>
                    )}
                  </div>
                )}

                {/* Questions */}
                {workflowInfo.questions.length > 0 && (
                  <div className="result-section">
                    <div
                      className="section-header"
                      onClick={() => toggleSection('questions')}
                    >
                      <h3>❓ Research Questions</h3>
                      <span className="toggle-icon">
                        {expandedSections.questions ? '▼' : '▶'}
                      </span>
                    </div>
                    {expandedSections.questions && (
                      <div className="section-content">
                        <ul className="questions-list">
                          {workflowInfo.questions.map((question, idx) => (
                            <li key={idx}>{question}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {/* Clarifications */}
                {Object.keys(workflowInfo.clarifications).length > 0 && (
                  <div className="result-section">
                    <div
                      className="section-header"
                      onClick={() => toggleSection('clarifications')}
                    >
                      <h3>💡 Clarifications</h3>
                      <span className="toggle-icon">
                        {expandedSections.clarifications ? '▼' : '▶'}
                      </span>
                    </div>
                    {expandedSections.clarifications && (
                      <div className="section-content">
                        <ReactMarkdown>{workflowInfo.clarifications.answer || 'No clarifications available'}</ReactMarkdown>
                      </div>
                    )}
                  </div>
                )}

                {/* Research Data */}
                {workflowInfo.chunks.length > 0 && (
                  <div className="result-section">
                    <div
                      className="section-header"
                      onClick={() => toggleSection('research')}
                    >
                      <h3>📚 Research Data ({workflowInfo.chunks.length} sources)</h3>
                      <span className="toggle-icon">
                        {expandedSections.research ? '▼' : '▶'}
                      </span>
                    </div>
                    {expandedSections.research && (
                      <div className="section-content">
                        <div className="research-chunks">
                          {workflowInfo.chunks.map((chunk, idx) => (
                            <div key={idx} className="chunk">
                              <div className="chunk-header">Source {idx + 1}</div>
                              <div className="chunk-content">{chunk}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Raw Data */}
                <div className="result-section">
                  <div
                    className="section-header"
                    onClick={() => toggleSection('raw')}
                  >
                    <h3>🔧 Raw Data</h3>
                    <span className="toggle-icon">
                      {expandedSections.raw ? '▼' : '▶'}
                    </span>
                  </div>
                  {expandedSections.raw && (
                    <div className="section-content">
                      <pre className="raw-data">{JSON.stringify(workflowInfo.rawResult, null, 2)}</pre>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="no-result">
                <p>No result data available</p>
              </div>
            )}
          </>
        ) : (
          <div className="no-selection">
            <p>Select a workflow to see details</p>
          </div>
        )}
      </main>
      {showStartModal && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>Start Workflow</h3>
            <select data-testid="template-select" value={newTemplate} onChange={e => setNewTemplate(e.target.value)}>
              {templates.map(t => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
            <input
              placeholder="Enter query..."
              value={newQuery}
              onChange={e => setNewQuery(e.target.value)}
            />
            <div className="modal-buttons">
              <button className="cancel-btn" onClick={cancelStartWorkflow}>Cancel</button>
              <button className="start-btn" onClick={confirmStartWorkflow}>Start</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
