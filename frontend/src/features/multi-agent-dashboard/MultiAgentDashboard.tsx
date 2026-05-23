import { AgentsTracker } from "./components/AgentsTracker";
import { ChatWorkspace } from "./components/ChatWorkspace";
import { LeftNavigation } from "./components/LeftNavigation";

export function MultiAgentDashboard() {
  return (
    <div className="h-full min-h-0 bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900 p-4 text-slate-100">
      <div className="grid h-full min-h-0 grid-cols-1 gap-4 md:grid-cols-[16rem_minmax(0,1fr)] xl:grid-cols-[16rem_minmax(0,1fr)_20rem]">
        <LeftNavigation />
        <ChatWorkspace />
        <AgentsTracker />
      </div>
    </div>
  );
}
