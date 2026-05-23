import {
  Download,
  Ellipsis,
  History,
  RotateCcw,
  SendHorizontal,
  Share2,
  Sparkles,
} from "lucide-react";

import { salesRows } from "../data";

function ChartPreview() {
  return (
    <div className="rounded-xl border border-slate-700/80 bg-slate-950/55 p-3">
      <div className="mb-2 flex items-center justify-between text-[10px] uppercase tracking-[0.16em] text-slate-500">
        <span>Revenue trend</span>
        <span>Q3</span>
      </div>
      <div className="relative h-28 overflow-hidden rounded-lg border border-slate-800/80 bg-gradient-to-b from-slate-900/75 to-slate-950/70">
        <svg viewBox="0 0 320 130" className="h-full w-full">
          <defs>
            <linearGradient id="lineGlow" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#60a5fa" />
              <stop offset="50%" stopColor="#818cf8" />
              <stop offset="100%" stopColor="#34d399" />
            </linearGradient>
          </defs>
          <g stroke="rgba(100,116,139,0.34)" strokeWidth="1">
            <line x1="0" y1="20" x2="320" y2="20" />
            <line x1="0" y1="50" x2="320" y2="50" />
            <line x1="0" y1="80" x2="320" y2="80" />
            <line x1="0" y1="110" x2="320" y2="110" />
          </g>
          <path
            d="M15 102 L75 84 L130 42 L190 63 L248 28 L305 18"
            fill="none"
            stroke="url(#lineGlow)"
            strokeWidth="4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path d="M15 102 L75 84 L130 42 L190 63 L248 28 L305 18 L305 130 L15 130 Z" fill="url(#lineGlow)" opacity="0.12" />
        </svg>
      </div>
    </div>
  );
}

function SalesTable() {
  return (
    <div className="rounded-xl border border-slate-700/80 bg-slate-950/55 p-3">
      <table className="w-full border-collapse text-left text-[11px]">
        <thead>
          <tr className="text-[10px] uppercase tracking-[0.12em] text-slate-500">
            <th className="border-b border-slate-800/80 pb-2 font-medium">Period</th>
            <th className="border-b border-slate-800/80 pb-2 font-medium">Revenue</th>
            <th className="border-b border-slate-800/80 pb-2 font-medium">Growth</th>
            <th className="border-b border-slate-800/80 pb-2 font-medium">Forecast</th>
          </tr>
        </thead>
        <tbody>
          {salesRows.map((row) => (
            <tr key={row.month} className="text-slate-300">
              <td className="border-b border-slate-900/90 py-1.5">{row.month}</td>
              <td className="border-b border-slate-900/90 py-1.5">{row.sales}</td>
              <td className="border-b border-slate-900/90 py-1.5">{row.growth}</td>
              <td className="border-b border-slate-900/90 py-1.5 text-emerald-300">{row.forecast}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ChatWorkspace() {
  return (
    <section className="flex min-h-[36rem] min-w-0 flex-col rounded-2xl border border-slate-800/60 bg-gradient-to-b from-slate-950/80 via-slate-950/70 to-slate-900/80 shadow-glow md:min-h-0">
      <header className="flex items-center justify-between border-b border-slate-800/60 px-5 py-4">
        <h2 className="text-xl font-semibold tracking-wide text-slate-100">CHAT</h2>
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="rounded-lg border border-slate-700/70 p-2 text-slate-400 transition-all duration-200 hover:border-slate-500 hover:text-slate-100"
            aria-label="Conversation history"
          >
            <History className="h-4 w-4" />
          </button>
          <button
            type="button"
            className="rounded-lg border border-slate-700/70 p-2 text-slate-400 transition-all duration-200 hover:border-slate-500 hover:text-slate-100"
            aria-label="More options"
          >
            <Ellipsis className="h-4 w-4" />
          </button>
        </div>
      </header>

      <div className="scrollbar-none flex-1 overflow-y-auto px-5 py-4">
        <div className="mx-auto max-w-5xl space-y-5">
          <div className="flex items-center gap-3">
            <div className="h-7 w-7 rounded-full border border-slate-700/80 bg-slate-800/80" />
            <div className="rounded-2xl border border-slate-700/80 bg-slate-900/75 px-4 py-2 text-sm text-slate-300">
              Analyze the Q3 sales performance data
            </div>
          </div>

          <div className="flex justify-end">
            <div className="max-w-[70%] rounded-2xl border border-indigo-400/30 bg-indigo-500/25 px-4 py-2 text-sm text-indigo-100">
              Analyze dtspaiman sales performance data
            </div>
          </div>

          <div className="flex items-start gap-3">
            <div className="mt-2 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-indigo-300/25 bg-indigo-500/25 text-indigo-200">
              <Sparkles className="h-4 w-4" />
            </div>

            <div className="min-w-0 flex-1">
              <article className="rounded-2xl border border-slate-700/80 bg-gradient-to-br from-slate-900/90 to-slate-950/80 p-5">
                <h3 className="text-2xl font-semibold tracking-wide text-slate-100">QUARTERLY SALES ANALYSIS (Q3)</h3>
                <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-300">
                  Quarterly sales performance data is identified to score Q3 outcomes against
                  targets. The current analysis indicates strong momentum in core segments while
                  identifying areas that require tighter budget control and conversion optimization.
                </p>

                <ul className="mt-4 list-disc space-y-2 pl-5 text-sm leading-7 text-slate-200 marker:text-indigo-300">
                  <li>
                    <strong className="font-semibold text-slate-100">Sales performance:</strong> Revenue
                    climbed steadily across Q3, with enterprise deals outperforming forecast.
                  </li>
                  <li>
                    <strong className="font-semibold text-slate-100">Analytics engine:</strong> Statistical
                    processing highlights margin improvements and lower churn in top accounts.
                  </li>
                  <li>
                    <strong className="font-semibold text-slate-100">Visualized statistics:</strong> Trend lines
                    show accelerating growth in late-quarter close velocity.
                  </li>
                  <li>
                    <strong className="font-semibold text-slate-100">Strategic recommendation:</strong> Expand
                    high-performing channels and rebalance spend from low-conversion campaigns.
                  </li>
                </ul>

                <div className="mt-5 grid gap-3 lg:grid-cols-2">
                  <ChartPreview />
                  <SalesTable />
                </div>

                <button
                  type="button"
                  className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl border border-indigo-400/45 bg-indigo-500/18 px-4 py-3 text-sm font-semibold uppercase tracking-[0.09em] text-indigo-100 transition-all duration-200 hover:bg-indigo-500/28"
                >
                  <Download className="h-4 w-4" />
                  Download as PDF
                </button>
              </article>

              <div className="mt-3 flex justify-end gap-2">
                <button
                  type="button"
                  className="rounded-xl border border-slate-700/80 bg-slate-900/70 px-3 py-2 text-xs font-medium uppercase tracking-[0.08em] text-slate-300 transition-all duration-200 hover:border-slate-500 hover:text-slate-100"
                >
                  <span className="inline-flex items-center gap-1.5">
                    <RotateCcw className="h-3.5 w-3.5" />
                    Regenerate
                  </span>
                </button>
                <button
                  type="button"
                  className="rounded-xl border border-slate-700/80 bg-slate-900/70 px-3 py-2 text-xs font-medium uppercase tracking-[0.08em] text-slate-300 transition-all duration-200 hover:border-slate-500 hover:text-slate-100"
                >
                  <span className="inline-flex items-center gap-1.5">
                    <Share2 className="h-3.5 w-3.5" />
                    Share
                  </span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="border-t border-slate-800/60 bg-slate-950/70 px-5 py-4">
        <div className="mx-auto max-w-5xl">
          <label className="relative block" htmlFor="agentPrompt">
            <input
              id="agentPrompt"
              type="text"
              placeholder="Type a new prompt here..."
              className="w-full rounded-xl border border-slate-700/80 bg-slate-900/80 px-4 py-3 pr-14 text-sm text-slate-200 outline-none transition-all duration-200 placeholder:text-slate-500 focus:border-indigo-400/70"
            />
            <button
              type="button"
              className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-lg border border-indigo-400/45 bg-indigo-500/25 p-2 text-indigo-200 transition-all duration-200 hover:bg-indigo-500/35"
              aria-label="Send message"
            >
              <SendHorizontal className="h-4 w-4" />
            </button>
          </label>
        </div>
      </div>
    </section>
  );
}
