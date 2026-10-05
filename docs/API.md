# API reference

Base URL: `http://127.0.0.1:8000/api`. JSON request/response. Все пути заканчиваются `/`. Multipart поддерживается при добавлении файла конспекта. Открытые пути: health, register, login; остальные требуют `Authorization: Token <token>`. Токен истекает через 24 часа; logout отзывает его.

## Authentication

```http
POST /api/auth/register/
Content-Type: application/json

{"username":"learner","password":"A-long-unique-password!"}
```

Ответ `201`:

```json
{"token":"<private-token>","user":{"id":1,"username":"learner"}}
```

Login: `POST /api/auth/login/` с теми же полями, ответ `200` той же формы. Имена регистронезависимы, сохраняются в нижнем регистре, разрешены латинские буквы, цифры и `_`, 3–30 символов. Минимум пароля — 10 символов; Django дополнительно запрещает частые пароли и сходство с именем. Неверная пара входа возвращает общий 400 без раскрытия существования аккаунта.

`GET /api/auth/me/` → `{"id":1,"username":"learner"}`. `POST /api/auth/logout/` → 204.

## Study material

```http
POST /api/material/
Authorization: Token <token>
Content-Type: application/json

{"topic":"embeddings","title":"Meaning as vectors","content":"An embedding is a vector representing meaning. Similar meanings are mapped to nearby vectors."}
```

Ответ `201` содержит `id`, `topic`, `title`, `content`, `created_at`. Тема нормализуется (нижний регистр, одиночные пробелы). Максимум: тема 100, заголовок 180, конспект 20,000 символов; минимум конспекта 30. При загрузке используйте multipart-поля `topic`, `title`, `file`, **без** `content`. Разрешены UTF-8 `.txt` и `.md` до 100 KB. Файл декодируется в текст и не исполняется.

`GET /api/material/` возвращает личные и общие учебные заметки, 30 на страницу. Пользовательские конспекты не становятся общедоступными.

## Generation and review

```http
POST /api/quizzes/generate/
Authorization: Token <token>
Content-Type: application/json

{"topic":"embeddings","difficulty":"beginner","count":2,"types":["multiple_choice","short_answer"],"adaptive":false}
```

Пример ответа `201` (IDs и содержание зависят от модели):

```json
{
  "id":7,"quizId":7,"title":"Embeddings (beginner)","topic":"embeddings",
  "difficulty":"beginner","status":"draft","version":1,"questionCount":2,
  "questions":[
    {"id":101,"type":"multiple_choice","text":"What is an embedding?",
     "options":["An embedding is a vector representing meaning.","An embedding is a byte count."],
     "expected":"An embedding is a vector representing meaning.",
     "source_quote":"An embedding is a vector representing meaning."},
    {"id":102,"type":"short_answer","text":"How does the model position similar meanings?","options":[],
     "expected":"Similar meanings are mapped to nearby vectors.",
     "source_quote":"Similar meanings are mapped to nearby vectors."}
  ],
  "ai":{"mode":"live","notice":"Real model questions; reference answers verified against the source."},
  "ai_mode":"live","adaptive":null
}
```

`difficulty`: beginner, intermediate, advanced. `count`: 1–10, не меньше количества типов. Типы уникальны. При `adaptive:true` итоговая сложность определяется по последним пяти попыткам, а поле `adaptive` объясняет решение. Без истории — beginner.

Если личных конспектов по теме нет, доступны общие seed-конспекты. Личные заметки имеют приоритет. Берутся до пяти последних конспектов по теме, суммарно до 20,000 символов; этот ограниченный снимок сохраняется в `Quiz.source_text`. Если источника нет: `400 {"topic":"Add study material for this topic first using /api/material/."}`.

`GET /api/quizzes/` — список с `topic`, `difficulty`, `status`, `search`, `page`. Общая форма пагинации:

```json
{"count":5,"next":null,"previous":null,"results":[]}
```

`GET /api/quizzes/7/` — представление для прохождения: **без expected и source_quote**. `GET /api/quizzes/7/review/` — эти поля доступны только автору. Авторское редактирование:

```http
PATCH /api/quizzes/7/
Authorization: Token <token>
Content-Type: application/json

{"version":1,"title":"My embeddings practice","status":"published"}
```

Ответ `200` содержит новую `version`. Для изменения вопросов передайте целиком массив `questions`, где каждый элемент содержит `type`, `text`, `options`, `expected`, опционально `source_quote`. ID при замене вопросов создаются заново. Для partial update вложенный вопрос всё равно должен содержать все обязательные поля; это замена, а не частичный патч самого вопроса.

`POST /api/quizzes/` позволяет создать собственный тест без генерации: `title`, `topic`, `difficulty`, `source_text`, `questions`, опционально `status`. Проверки структуры такие же. `PUT` требует полный набор обязательных полей. Изменение/удаление теста после появления попыток запрещено. Это защищает смысл истории.

## Submit and results

```http
POST /api/quizzes/7/submit/
Authorization: Token <token>
Idempotency-Key: 55e50898-ccce-45e3-9ee6-1e7e1525a21a
Content-Type: application/json

{"quizId":7,"answers":[
  {"questionId":101,"selectedAnswer":"An embedding is a vector representing meaning.","timeSpent":15},
  {"questionId":102,"selectedAnswer":"Related concepts occupy neighboring points in the numerical space.","timeSpent":22}
]}
```

Отправьте **каждый вопрос ровно один раз**. Для пропуска — `selectedAnswer:""`. `selectedAnswer` — текст варианта, не его буква или индекс; буквы A/B/C служат только для интерфейса. `timeSpent` — целое число секунд 0–86,400; максимум ответа — 4,000 символов. Поле `quizId` необязательно, но при наличии должно совпадать с URL.

Ответ `201` на первую запись, `200` на точный повтор:

```json
{
  "id":12,"quizId":7,"title":"My embeddings practice","topic":"embeddings","difficulty":"beginner",
  "score":100.0,"correct_count":2,"total_questions":2,"time_spent":37,"ai_mode":"live",
  "answers":[
    {"questionId":101,"type":"multiple_choice","question":"What is an embedding?",
     "selectedAnswer":"An embedding is a vector representing meaning.","expected":"An embedding is a vector representing meaning.",
     "timeSpent":15,"verdict":"correct","score":1.0,"justification":"Exact option match.","ai_mode":"deterministic"},
    {"questionId":102,"type":"short_answer","question":"How does the model position similar meanings?",
     "selectedAnswer":"Related concepts occupy neighboring points in the numerical space.",
     "expected":"Similar meanings are mapped to nearby vectors.","timeSpent":22,
     "verdict":"correct","score":0.9,"justification":"Preserves the relationship between meaning and vector proximity.","ai_mode":"live"}
  ]
}
```

Ключ — UUID. На повторе передайте **тот же ключ и те же данные**. Изменённые данные с прежним ключом → 409. Вопросы проверяются до вызова модели. Длительная проверка модели проходит вне транзакции БД. Затем версия теста повторно проверяется под блокировкой, и попытка с ответами записываются атомарно. Конкурирующие повторы возвращают одну и ту же попытку.

`/results/:id` во frontend использует **ID попытки**, а не теста. `GET /api/attempts/12/` доступен только владельцу результата. `GET /api/profile/history/` → `{user, attempts, totalAttempts}` (последние 100); для полной постраничной истории — `GET /api/attempts/?page=...`.

## Bonuses

`POST /api/quizzes/7/analyze/` с `{"attemptId":12}` анализирует конкретную свою попытку; без поля — последнюю свою попытку этого теста.

```json
{
  "attemptId":12,"overallScore":100,"correctCount":2,"totalQuestions":2,"timeSpent":37,
  "categories":[{"topic":"embeddings","accuracy":100,"averageSeconds":18.5}],
  "strengths":["You relate meaning to vector proximity."],
  "weaknesses":["Continue testing the boundaries of your understanding."],
  "recommendations":["Explain semantic search with a new example."],
  "nextSteps":"Practice retrieval with unfamiliar documents.",
  "ai":{"mode":"live","notice":"Real language model response."}
}
```

Все числовые поля вычисляет backend из сохранённой попытки. В модели каждого теста одна тема, поэтому `categories` содержит одну тематическую запись. Модель получает вычисленные значения и пишет качественные пояснения; числовые утверждения и `%` в её тексте отклоняются.

`GET /api/recommendations/` → `{recommendations:[{quizId,title,topic,reason}],ai}`. ORM считает средний результат по темам. Модель выбирает до трёх доступных опубликованных тестов, ID проверяются по реальной библиотеке. В fallback сначала рекомендуются ещё не пройденные темы, затем более слабые.

`GET /api/profile/difficulty/` → `{difficulty,reason,attemptsUsed,ai}`. Используются только последние пять попыток. Модель может сдвинуть уровень максимум на одну ступень. Offline-правило: средний результат ≥80% — на ступень вверх; <50% — вниз; иначе сохранить уровень. Диапазон ограничен beginner…advanced.

## Failures and boundaries

- `400`: некорректный JSON, поля, файл, ответы, отсутствующие конспекты или попытка отправить draft.
- `401`: нет токена, токен отозван/истёк.
- `403`: попытка изменить общий тест или получить его авторское review.
- `404`: отсутствующий/чужой личный объект; чужие данные не раскрываются.
- `409`: устаревшая версия, изменение теста с попытками, конфликт idempotency key.
- `413`: слишком большой/нечитаемый запрос.
- `429`: лимит запросов; повторить после `Retry-After`.
- `503`: временно недоступна БД; повторить запрос, сохранив ключ отправки.

Модель: таймаут, разрыв соединения, 429/500, отсутствие конфигурации, слишком большой ответ, невалидный JSON/оценка → прозрачный `mock` либо `fallback`, а не выдуманный успех живой модели. Генератор может один раз попросить исправить неверную структуру; сетевые ошибки автоматически не повторяются. Ответ провайдера ограничен 150 KB. Числа NaN/Infinity и оценки вне [0,1] отклоняются.

`GET /health/` сообщает, настроена ли модель, но не обещает её доступность. Фактический режим указан в каждом AI-результате. Авторитетными остаются исходный материал и вычисленные backend-метрики; качество открытого ответа модели зависит от выбранной LLM.
