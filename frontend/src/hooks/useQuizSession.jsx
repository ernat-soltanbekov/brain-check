import { createContext, useContext, useState } from 'react'
import { storage, readJSON } from '../utils/storage'
const SessionContext = createContext(null)
export function QuizSessionProvider({ quiz, userId, children }) {
  const key = `brain-check.session.${userId}.${quiz.id}.${quiz.version}`
  const [session, setSession] = useState(() => {
    const saved = readJSON(key)
    return saved &&
      Array.isArray(saved.answers) &&
      saved.answers.length === quiz.questions.length &&
      saved.answers.every(
        (a, i) =>
          a &&
          a.questionId === quiz.questions[i].id &&
          typeof a.selectedAnswer === 'string' &&
          a.selectedAnswer.length <= 4000 &&
          Number.isInteger(a.timeSpent) &&
          a.timeSpent >= 0 &&
          a.timeSpent <= 86400,
      ) &&
      Number.isInteger(saved.index) &&
      saved.index >= 0 &&
      saved.index < quiz.questions.length
      ? saved
      : {
          index: 0,
          answers: quiz.questions.map((q) => ({
            questionId: q.id,
            selectedAnswer: '',
            timeSpent: 0,
          })),
          pending: null,
        }
  })
  function update(updater) {
    setSession((previous) => {
      const next = typeof updater === 'function' ? updater(previous) : updater
      storage.set(key, JSON.stringify(next))
      return next
    })
  }
  return (
    <SessionContext.Provider value={{ session, update, clear: () => storage.remove(key) }}>
      {children}
    </SessionContext.Provider>
  )
}
export const useQuizSession = () => useContext(SessionContext)
