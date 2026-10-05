"""Small hand-authored reference quizzes; model generation remains a separate feature."""


def pair(mc, options, expected, short, reference):
    return [
        {"type": "multiple_choice", "text": mc, "options": options, "expected": expected},
        {"type": "short_answer", "text": short, "options": [], "expected": reference},
    ]


QUESTIONS = {
    "python data structures": pair(
        "Which Python collection stores unique elements?",
        ["list", "set", "tuple", "str"],
        "set",
        "When would you use a dictionary?",
        "A dictionary maps unique keys to values for fast lookup.",
    ),
    "embeddings": pair(
        "What is a text embedding?",
        ["A vector representing meaning", "A compressed image", "A database index"],
        "A vector representing meaning",
        "Why are similar texts close in embedding space?",
        "The model maps texts with similar meanings to nearby vectors.",
    ),
    "rag": pair(
        "What does retrieval add to a language model prompt?",
        ["Random weights", "Relevant source passages", "A new optimizer"],
        "Relevant source passages",
        "Why should a RAG answer cite its sources?",
        "Citations let readers verify the answer against retrieved evidence.",
    ),
    "prompting": pair(
        "What makes a structured output easier to validate?",
        ["An explicit JSON schema", "A longer greeting", "No constraints"],
        "An explicit JSON schema",
        "Why separate instructions from supplied documents?",
        "Documents are untrusted data and must not override the system instructions.",
    ),
    "go concurrency": pair(
        "What is a Go channel used for?",
        ["Sharing values between goroutines", "Compiling code", "Defining a package"],
        "Sharing values between goroutines",
        "How can context cancellation help a concurrent program?",
        "Context cancellation signals goroutines to stop work and release resources.",
    ),
}
