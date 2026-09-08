"use client";

import { FormEvent, useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

type Activity = {
  type: string;
  message?: string;
  tool?: string;
  input?: unknown;
  output?: string;
};

export default function Home() {
  const [email, setEmail] = useState("");
  const [instructions, setInstructions] = useState("");
  const [resume, setResume] = useState<File | null>(null);

  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState("ready");
  const [activity, setActivity] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(false);

  async function startRun(event: FormEvent) {
    event.preventDefault();

    setLoading(true);
    setActivity([]);

    const formData = new FormData();

    if (resume) {
      formData.append("resume", resume);
    }

    formData.append("to_email", email);
    formData.append("additional_instructions", instructions);

    const response = await fetch(`${API_URL}/api/runs`, {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (data.error) {
      setActivity([
        {
          type: "error",
          message: data.error,
        },
      ]);

      setLoading(false);
      return;
    }

    setRunId(data.run_id);
    setStatus("running");
  }

  useEffect(() => {
    if (!runId) {
      return;
    }

    const source = new EventSource(`${API_URL}/api/runs/${runId}/events`);

    source.onmessage = (event) => {
      const data: Activity = JSON.parse(event.data);

      setActivity((current) => [...current, data]);

      if (data.type === "complete") {
        setStatus("complete");
        setLoading(false);
        source.close();
      }

      if (data.type === "error") {
        setStatus("failed");
        setLoading(false);
        source.close();
      }
    };

    source.onerror = () => {
      source.close();
    };

    return () => source.close();
  }, [runId]);

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto max-w-5xl px-6 py-10">
        <header className="mb-10 flex items-center justify-between">
          <div>
            <div className="mb-2 text-sm font-medium text-blue-400">
              JOB SCOUT
            </div>

            <h1 className="text-4xl font-semibold tracking-tight">
              Find your next opportunity.
            </h1>

            <p className="mt-2 text-slate-400">
              AI-powered job matching based on your resume.
            </p>
          </div>

          <div className="rounded-full border border-slate-800 bg-slate-900 px-4 py-2 text-sm">
            <span className="mr-2 inline-block h-2 w-2 rounded-full bg-green-400" />
            {status === "running"
              ? "Agent running"
              : status === "complete"
                ? "Complete"
                : "Ready"}
          </div>
        </header>

        <form onSubmit={startRun} className="space-y-6">
          <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl">
            <h2 className="text-lg font-medium">Resume</h2>

            <p className="mt-1 text-sm text-slate-400">
              Upload your latest PDF resume.
            </p>

            <div className="mt-5 rounded-xl border border-dashed border-slate-700 p-5">
              <input
                type="file"
                accept=".pdf"
                onChange={(event) => setResume(event.target.files?.[0] || null)}
                className="block w-full text-sm text-slate-400"
              />

              {resume && (
                <p className="mt-3 text-sm text-green-400">✓ {resume.name}</p>
              )}
            </div>
          </section>

          <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl">
            <h2 className="text-lg font-medium">Email</h2>

            <input
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              className="mt-4 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 outline-none transition focus:border-blue-500"
            />
          </section>

          <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl">
            <h2 className="text-lg font-medium">Additional instructions</h2>

            <textarea
              value={instructions}
              onChange={(event) => setInstructions(event.target.value)}
              placeholder="e.g. Prioritize backend roles and companies with strong engineering culture."
              rows={4}
              className="mt-4 w-full resize-none rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 outline-none transition focus:border-blue-500"
            />
          </section>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-blue-500 px-6 py-4 font-medium transition hover:bg-blue-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Agent is running..." : "✨ Find matching jobs"}
          </button>
        </form>

        <section className="mt-10 rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-medium">Agent Activity</h2>

              <p className="mt-1 text-sm text-slate-400">
                Live progress from your job search.
              </p>
            </div>
          </div>

          <div className="mt-6 space-y-3">
            {activity.length === 0 && (
              <div className="rounded-xl bg-slate-950 p-5 text-sm text-slate-500">
                Activity will appear here when the agent starts.
              </div>
            )}

            {activity.map((item, index) => (
              <ActivityItem key={index} activity={item} />
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}

function ActivityItem({ activity }: { activity: Activity }) {
  if (activity.type === "tool_call") {
    return (
      <details className="rounded-xl border border-slate-800 bg-slate-950 p-4">
        <summary className="cursor-pointer text-sm font-medium">
          🔧 {activity.tool}
        </summary>

        <pre className="mt-3 overflow-auto text-xs text-slate-500">
          {JSON.stringify(activity.input, null, 2)}
        </pre>
      </details>
    );
  }

  if (activity.type === "tool_result") {
    return (
      <details className="rounded-xl border border-slate-800 bg-slate-950 p-4">
        <summary className="cursor-pointer text-sm font-medium text-slate-300">
          ✓ {activity.tool} completed
        </summary>

        <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap text-xs text-slate-500">
          {activity.output}
        </pre>
      </details>
    );
  }

  if (activity.type === "error") {
    return (
      <div className="rounded-xl border border-red-900 bg-red-950/40 p-4 text-sm text-red-300">
        ✕ {activity.message}
      </div>
    );
  }

  if (activity.type === "complete") {
    return (
      <div className="rounded-xl border border-green-900 bg-green-950/40 p-4 text-sm text-green-300">
        ✓ {activity.message}
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300">
      <span className="mr-2 text-blue-400">●</span>
      {activity.message}
    </div>
  );
}
