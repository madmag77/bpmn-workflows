import { useState, useEffect } from 'react'
import './App.css'

export default function App() {
  const [workflows, setWorkflows] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    fetch('/workflows')
      .then(r => r.json())
      .then(data => {
        setWorkflows(data)
        if (data.length > 0) {
          setSelectedId(data[0].id)
        }
      })
  }, [])

  useEffect(() => {
    if (!selectedId) return
    fetch(`/workflows/${selectedId}`)
      .then(r => r.json())
      .then(setSelected)
  }, [selectedId])

  const startWorkflow = async () => {
    const query = window.prompt('Enter query for workflow:') || ''
    const resp = await fetch('/workflows', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ template_id: 'deepresearch', query })
    })
    const data = await resp.json()
    setWorkflows([...workflows, { id: data.id, template: 'deepresearch', status: data.status }])
    setSelectedId(data.id)
    setSelected(data)
  }

  const continueWorkflow = async answer => {
    const resp = await fetch(`/workflows/${selectedId}/continue`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: answer })
    })
    const data = await resp.json()
    setWorkflows(workflows.map(w => (w.id === selectedId ? { ...w, status: data.status } : w)))
    setSelected(data)
  }

  const [answer, setAnswer] = useState('')
  const interrupt = selected?.result?.__interrupt__?.[0]

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
              <span className={`state state-${w.status.replace(/\s+/g, '-').toLowerCase()}`}>{w.status}</span>
            </li>
          ))}
        </ul>
        <button className="new-workflow" onClick={startWorkflow}>Start New Workflow</button>
      </aside>
      <main className="content">
        {selected ? (
          <>
            <h2>{selected.template}</h2>
            <p>Status: <strong>{selected.status}</strong></p>
            {interrupt ? (
              <div className="workflow-content">
                <p>{interrupt.value.questions.join('\n')}</p>
                <input value={answer} onChange={e => setAnswer(e.target.value)} placeholder="Answer" />
                <button onClick={() => { continueWorkflow(answer); setAnswer(''); }}>Continue</button>
              </div>
            ) : (
              <pre className="workflow-content">{JSON.stringify(selected.result, null, 2)}</pre>
            )}
          </>
        ) : (
          <p>Select a workflow to see details</p>
        )}
      </main>
    </div>
  )
}
