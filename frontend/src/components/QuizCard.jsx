import { ArrowUpRight, Braces, Cpu, GitBranch, Layers, MessageSquareText } from 'lucide-react'
import { Link } from '@tanstack/react-router'
const icons = {
  'python data structures': Braces,
  embeddings: Cpu,
  rag: Layers,
  prompting: MessageSquareText,
  'go concurrency': GitBranch,
}
export default function QuizCard({ quiz, index = 0 }) {
  const Icon = icons[quiz.topic] || Layers
  return (
    <article className="quiz-card">
      <div className="card-top">
        <span className={`topic-icon tone-${index % 4}`}>
          <Icon size={24} />
        </span>
        <span className="difficulty">{quiz.difficulty}</span>
      </div>
      <p className="eyebrow">{quiz.topic}</p>
      <h3>{quiz.title}</h3>
      <p className="card-description">
        {quiz.status === 'draft'
          ? 'Review the questions, refine the answers, then save your practice.'
          : 'Build a clearer understanding, one question at a time.'}
      </p>
      <div className="card-bottom">
        <span>
          {quiz.questionCount} questions <span>·</span>{' '}
          {quiz.status === 'draft' ? 'Draft' : 'Self-paced'}
        </span>
        <Link
          className="circle-link"
          aria-label={`${quiz.status === 'draft' ? 'Review' : 'Start'} ${quiz.title}`}
          to={quiz.status === 'draft' ? '/review/$id' : '/quiz/$id'}
          params={{ id: String(quiz.id) }}
        >
          <ArrowUpRight size={21} />
        </Link>
      </div>
    </article>
  )
}
