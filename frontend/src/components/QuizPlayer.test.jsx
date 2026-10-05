import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import QuizPlayer from './QuizPlayer'
import { QuizSessionProvider } from '../hooks/useQuizSession'
import { storage } from '../utils/storage'
import { api } from '../utils/apiClient'
vi.mock('@tanstack/react-router', () => ({ useNavigate: () => vi.fn() }))
vi.mock('../utils/apiClient', () => ({ api: vi.fn() }))
const quiz = {
  id: 99,
  version: 1,
  title: 'Concept check',
  difficulty: 'beginner',
  ai_mode: 'mock',
  questions: [
    { id: 1, type: 'multiple_choice', text: 'Choose the supported fact.', options: ['A', 'B'] },
    { id: 2, type: 'short_answer', text: 'Explain your reasoning.', options: [] },
  ],
}
const key = 'brain-check.session.1.99.1'
function setup() {
  return render(
    <QuizSessionProvider quiz={quiz} userId={1}>
      <QuizPlayer quiz={quiz} />
    </QuizSessionProvider>,
  )
}
beforeEach(() => {
  storage.remove(key)
  vi.clearAllMocks()
})
it('restores answers and current question after remount', () => {
  const view = setup()
  fireEvent.click(screen.getByRole('radio', { name: /A/ }))
  fireEvent.click(screen.getByRole('button', { name: 'Next question' }))
  fireEvent.change(screen.getByLabelText('Your answer'), {
    target: { value: 'A clear explanation.' },
  })
  view.unmount()
  setup()
  expect(screen.getByLabelText('Your answer')).toHaveValue('A clear explanation.')
  expect(screen.getByText('2 answered')).toBeInTheDocument()
})
it('retries a failed submission with the original key and frozen answers', async () => {
  api.mockRejectedValueOnce(new Error('Network unavailable')).mockResolvedValueOnce({ id: 7 })
  setup()
  fireEvent.click(screen.getByRole('radio', { name: /A/ }))
  fireEvent.click(screen.getByRole('button', { name: 'Next question' }))
  fireEvent.change(screen.getByLabelText('Your answer'), { target: { value: 'My answer' } })
  fireEvent.click(screen.getByRole('button', { name: 'Review & submit' }))
  fireEvent.click(screen.getByRole('button', { name: 'Submit answers' }))
  await screen.findByText('Network unavailable')
  expect(screen.getByLabelText('Your answer')).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Retry saved submission' }))
  await waitFor(() => expect(api).toHaveBeenCalledTimes(2))
  expect(api.mock.calls[0][1].headers).toEqual(api.mock.calls[1][1].headers)
  expect(api.mock.calls[0][1].body).toEqual(api.mock.calls[1][1].body)
})
it('does not crash on corrupted stored answers', () => {
  storage.set(key, JSON.stringify({ index: 0, answers: [null, null] }))
  setup()
  expect(screen.getByText('Choose the supported fact.')).toBeInTheDocument()
})
