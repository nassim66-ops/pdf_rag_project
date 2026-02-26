import React, { useState } from "react";
import "./App.css";

interface Source {
  pdf: string;
  page: number;
  snippet: string;
}

interface Response {
  answer: string;
  sources: Source[];
}

function App() {
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<Response | null>(null);
  const [loading, setLoading] = useState(false);
  const [openSources, setOpenSources] = useState<{ [key: number]: boolean }>({});

  const handleAskQuestion = async () => {
    if (!question.trim()) return;

    setLoading(true);
    setResponse(null);

    try {
      const res = await fetch("http://127.0.0.1:8000/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });

      const data: Response = await res.json();
      setResponse(data);
      setOpenSources({});
    } catch (err) {
      setResponse({ answer: "Error fetching response.", sources: [] });
    } finally {
      setLoading(false);
    }
  };

  const toggleSource = (index: number) => {
    setOpenSources((prev) => ({ ...prev, [index]: !prev[index] }));
  };

  const highlightKeywords = (text: string, keywords: string[]) => {
    const cleanKeywords = keywords.filter(k => k.length > 3);
    if (!cleanKeywords.length) return text;

    const regex = new RegExp(`(${cleanKeywords.join("|")})`, "gi");

    return text.split(regex).map((part, i) =>
      regex.test(part) ? <mark key={i}>{part}</mark> : part
    );
  };

  return (
    <div className="app">
      <div className="card">
        <h1>AI Knowledge Assistant</h1>

        <textarea
        className="textarea"
          placeholder="Ask something about your documents..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleAskQuestion()}
        />

        <button
          onClick={handleAskQuestion}
          disabled={loading || !question.trim()}
        >
          {loading ? "Analyzing..." : "Ask Question"}
        </button>

        {!response && !loading && (
          <div className="empty-state">
            Ask a question to retrieve relevant answers and sources.
          </div>
        )}

        {response && (
          <div className="response">
            <h2>Answer</h2>
            <p>{response.answer}</p>

            {response.sources.length > 0 && (
              <div className="sources">
                <h3>Sources</h3>

                {response.sources.map((src, index) => (
                  <div key={index} className="source">
                    <div
                      className="source-header"
                      onClick={() => toggleSource(index)}
                    >
                      <div>
                        <strong>{src.pdf}</strong>
                        <span className="page">Page {src.page}</span>
                      </div>
                      <span className="arrow">
                        {openSources[index] ? "−" : "+"}
                      </span>
                    </div>

                    {openSources[index] && (
                      <div className="snippet">
                        {highlightKeywords(
                          src.snippet,
                          question.split(" ")
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;