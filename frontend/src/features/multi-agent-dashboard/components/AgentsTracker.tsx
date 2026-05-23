import {
  BarChart3,
  Check,
  CheckCircle2,
  Database,
  EllipsisVertical,
  Loader2,
  Settings2,
  UserRound,
} from "lucide-react";

type TrackerNodeProps = {
  title: string;
  subtitle: string;
  icon: React.ReactNode;
  status: "done" | "running";
  chip?: string;
};

function TrackerNode({ title, subtitle, icon, status, chip }: TrackerNodeProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3 rounded-xl border border-slate-800/70 bg-slate-900/75 px-3 py-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-700/70 bg-slate-800/80 text-slate-300">
          {icon}
        </div>

        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold uppercase tracking-[0.03em] text-slate-100">{title}</p>
          <p className="truncate text-sm text-slate-400">{subtitle}</p>
        </div>

        {status === "done" ? (
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-300">
            <Check className="h-4 w-4" />
          </span>
        ) : (
          <span className="flex h-6 w-6 items-center justify-center rounded-full border border-indigo-400/40 bg-indigo-500/15 text-indigo-300">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          </span>
        )}
      </div>

      {chip && (
        <div className="ml-auto flex w-fit items-center gap-2 rounded-full border border-slate-700/70 bg-slate-900/90 px-3 py-1 text-xs text-slate-300">
          {status === "running" && <Loader2 className="h-3 w-3 animate-spin text-indigo-300" />}
          {status === "done" && <CheckCircle2 className="h-3 w-3 text-emerald-300" />}
          <span>{chip}</span>
        </div>
      )}
    </div>
  );
}

export function AgentsTracker() {
  return (
    <aside className="flex min-h-[24rem] min-w-0 flex-col rounded-2xl border border-slate-800/60 bg-gradient-to-b from-slate-950/90 via-slate-950/80 to-slate-900/75 shadow-glow md:min-h-0 md:col-span-2 xl:col-span-1">
      <header className="flex items-center justify-between border-b border-slate-800/60 px-4 py-4">
        <h2 className="text-base font-semibold tracking-wide text-slate-100">ACTIVE AGENTS &amp; SUBAGENTS</h2>
        <button
          type="button"
          className="rounded-lg border border-slate-700/70 p-2 text-slate-400 transition-all duration-200 hover:border-slate-500 hover:text-slate-100"
          aria-label="More agent options"
        >
          <EllipsisVertical className="h-4 w-4" />
        </button>
      </header>

      <div className="scrollbar-none flex-1 overflow-y-auto p-4">
        <div className="space-y-3">
          <TrackerNode
            title="USER REQUEST"
            subtitle="Input"
            icon={<UserRound className="h-4 w-4" />}
            status="done"
            chip="Status update..."
          />

          <div className="ml-5 border-l border-slate-700/80 pl-5">
            <TrackerNode
              title="ORCHESTRATOR AGENT"
              subtitle="Managing"
              icon={<Settings2 className="h-4 w-4" />}
              status="done"
            />

            <div className="mt-3 space-y-3 border-l border-indigo-400/35 pl-4">
              <TrackerNode
                title="SUBAGENT 1: DATA FETCHER"
                subtitle="Fetching from DB"
                icon={<Database className="h-4 w-4" />}
                status="done"
                chip="Fetching from DB"
              />

              <TrackerNode
                title="SUBAGENT 2: ANALYTICS ENGINE"
                subtitle="Processing statistics"
                icon={<Loader2 className="h-4 w-4 animate-spin" />}
                status="running"
                chip="Processing statistics"
              />

              <TrackerNode
                title="SUBAGENT 3: VISUALIZER"
                subtitle="Creating chart"
                icon={<BarChart3 className="h-4 w-4" />}
                status="done"
                chip="Creating chart"
              />
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
