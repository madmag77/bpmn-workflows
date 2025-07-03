import { /** @type {WorkflowHistory[]} */ null as _ } from './models.js'

/**
 * Fetch list of workflow runs.
 * @returns {Promise<WorkflowHistory[]>}
 */
export async function getWorkflows() {
  const resp = await fetch('/workflows')
  return resp.json()
}

/**
 * Fetch workflow details.
 * @param {string} id
 * @returns {Promise<WorkflowDetail>}
 */
export async function getWorkflow(id) {
  const resp = await fetch(`/workflows/${id}`)
  return resp.json()
}

/**
 * Start a new workflow.
 * @param {string} template
 * @param {string} query
 * @returns {Promise<WorkflowResponse>}
 */
export async function startWorkflow(template, query) {
  const resp = await fetch('/workflows', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ template_name: template, query })
  })
  return resp.json()
}

/**
 * Continue a workflow waiting for input.
 * @param {string} id
 * @param {string} answer
 * @returns {Promise<WorkflowResponse>}
 */
export async function continueWorkflow(id, answer) {
  const resp = await fetch(`/workflows/${id}/continue`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: answer })
  })
  return resp.json()
}
