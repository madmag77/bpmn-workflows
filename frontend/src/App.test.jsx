import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
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

test('workflows display in finished, in progress and waiting states', async () => {
  fetch.mockImplementation((url) => {
    if (url === '/workflows') {
      return mockResponse([
        { id: '1', template: 'a', status: 'in progress' },
        { id: '2', template: 'b', status: 'waiting for user' },
        { id: '3', template: 'c', status: 'finished' }
      ]);
    }
    return mockResponse({ id: '1', template: 'a', status: 'in progress', result: {} });
  });

  render(<App />);

  await waitFor(() => expect(fetch).toHaveBeenCalledWith('/workflows'));
  await screen.findAllByRole('listitem');

  expect(document.querySelector('.state-in-progress')).toBeTruthy();
  expect(document.querySelector('.state-waiting-for-user')).toBeTruthy();
  expect(document.querySelector('.state-finished')).toBeTruthy();
});

test('user can start new workflow with query', async () => {
  fetch.mockImplementation((url, options) => {
    if (url === '/workflows' && !options) {
      return mockResponse([]);
    }
    if (url === '/workflows' && options?.method === 'POST') {
      return mockResponse({ id: '10', template: 'deepresearch', status: 'in progress', result: {} });
    }
    if (url === '/workflows/10') {
      return mockResponse({ id: '10', template: 'deepresearch', status: 'in progress', result: {} });
    }
    return mockResponse({});
  });

  jest.spyOn(window, 'prompt').mockReturnValue('my query');

  render(<App />);

  fireEvent.click(screen.getByText(/Start New Workflow/));

  await waitFor(() => expect(fetch).toHaveBeenCalledWith('/workflows', expect.objectContaining({ method: 'POST' })));

  expect(await screen.findByText('in progress')).toBeInTheDocument();
});

test('user can continue waiting workflow', async () => {
  fetch.mockImplementation((url, options) => {
    if (url === '/workflows' && !options) {
      return mockResponse([{ id: '5', template: 'deepresearch', status: 'waiting for user' }]);
    }
    if (url === '/workflows/5') {
      return mockResponse({
        id: '5',
        template: 'deepresearch',
        status: 'waiting for user',
        result: { __interrupt__: [{ value: { questions: ['clarify?'] } }] }
      });
    }
    if (url === '/workflows/5/continue') {
      return mockResponse({ id: '5', template: 'deepresearch', status: 'finished', result: { final_answer: 'done' } });
    }
    return mockResponse({});
  });

  render(<App />);

  await screen.findByText('waiting for user');
  await screen.findByPlaceholderText('Answer');

  fireEvent.change(screen.getByPlaceholderText('Answer'), { target: { value: 'ok' } });
  fireEvent.click(screen.getByText('Continue'));

  await waitFor(() => expect(fetch).toHaveBeenCalledWith('/workflows/5/continue', expect.objectContaining({ method: 'POST' })));

  const elems = await screen.findAllByText('finished');
  expect(elems.length).toBeGreaterThan(0);
});
