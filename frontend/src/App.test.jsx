import '@testing-library/jest-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import App from './App';

beforeEach(() => {
  global.fetch = jest.fn();
});

afterEach(() => {
  jest.resetAllMocks();
});

function mockResponse(data) {
  return Promise.resolve({ ok: true, json: () => Promise.resolve(data) });
}

test('workflows display in succeeded, running and waiting states', async () => {
  fetch.mockImplementation((url) => {
    if (url === '/workflows') {
      return mockResponse([
        { id: '1', template: 'a', status: 'running' },
        { id: '2', template: 'b', status: 'needs_input' },
        { id: '3', template: 'c', status: 'succeeded' }
      ]);
    }
    return mockResponse({ id: '1', template: 'a', status: 'running', result: {} });
  });

  render(<App />);

  await waitFor(() => expect(fetch).toHaveBeenCalledWith('/workflows'));
  await screen.findAllByRole('listitem');

  expect(document.querySelector('.state-running')).toBeTruthy();
  expect(document.querySelector('.state-needs_input')).toBeTruthy();
  expect(document.querySelector('.state-succeeded')).toBeTruthy();
});

test('user can start new workflow with query', async () => {
  fetch.mockImplementation((url, options) => {
    if (url === '/workflows' && !options) {
      return mockResponse([]);
    }
    if (url === '/workflows' && options?.method === 'POST') {
      return mockResponse({ id: '10', template: 'deepresearch', status: 'running', result: {} });
    }
    if (url === '/workflows/10') {
      return mockResponse({ id: '10', template: 'deepresearch', status: 'running', result: {} });
    }
    return mockResponse({});
  });

  jest.spyOn(window, 'prompt').mockReturnValue('my query');

  render(<App />);

  fireEvent.click(screen.getByText(/Start New Workflow/));

  await waitFor(() => expect(fetch).toHaveBeenCalledWith('/workflows', expect.objectContaining({ method: 'POST' })));

  const runningElements = await screen.findAllByText('running');
  expect(runningElements.length).toBeGreaterThan(0);
});

test('user can continue waiting workflow', async () => {
  fetch.mockImplementation((url, options) => {
    if (url === '/workflows' && !options) {
      return mockResponse([{ id: '5', template: 'deepresearch', status: 'needs_input' }]);
    }
    if (url === '/workflows/5') {
      return mockResponse({
        id: '5',
        template: 'deepresearch',
        status: 'needs_input',
        result: { __interrupt__: [{ value: { questions: ['clarify?'] } }] }
      });
    }
    if (url === '/workflows/5/continue') {
      return mockResponse({ id: '5', template: 'deepresearch', status: 'succeeded', result: { final_answer: 'done' } });
    }
    return mockResponse({});
  });

  render(<App />);

  await screen.findByText('needs_input');
  await screen.findByPlaceholderText('Answer');

  fireEvent.change(screen.getByPlaceholderText('Answer'), { target: { value: 'ok' } });
  fireEvent.click(screen.getByText('Continue'));

  await waitFor(() => expect(fetch).toHaveBeenCalledWith('/workflows/5/continue', expect.objectContaining({ method: 'POST' })));

  const elems = await screen.findAllByText('succeeded');
  expect(elems.length).toBeGreaterThan(0);
});
