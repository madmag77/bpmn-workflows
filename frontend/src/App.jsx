import { useState } from 'react'
import './App.css'

const initialWorkflows = [
  { id: 1, title: 'Example Research', state: 'In progress', content: 'Loading...' },
  { id: 2, title: 'Another Workflow', state: 'Waiting for user', content: 'Provide more info...' },
  { id: 3, title: 'Finished Workflow', state: 'Finished', content: 'Result summary' }
]

export default function App() {
  const [workflows, setWorkflows] = useState(initialWorkflows)
  const [selectedId, setSelectedId] = useState(workflows[0]?.id)

  const startWorkflow = () => {
    const newId = workflows.length + 1
    const newWorkflow = {
      id: newId,
      title: `New Workflow ${newId}`,
      state: 'In progress',
      content: 'New workflow started'
    }
    setWorkflows([...workflows, newWorkflow])
    setSelectedId(newId)
  }

  const selected = workflows.find(w => w.id === selectedId)

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
              <span className="title">{w.title}</span>
              <span className={`state state-${w.state.replace(/\s+/g, '-').toLowerCase()}`}>{w.state}</span>
            </li>
          ))}
        </ul>
        <button className="new-workflow" onClick={startWorkflow}>Start New Workflow</button>
      </aside>
      <main className="content">
        {selected ? (
          <>
            <h2>{selected.title}</h2>
            <p>Status: <strong>{selected.state}</strong></p>
            <div className="workflow-content">{selected.content}</div>
          </>
        ) : (
          <p>Select a workflow to see details</p>
        )}
      </main>
    </div>
  )
}
