import { useEffect, useState } from "react";

import { ChatContainer } from "./ChatContainer";
import { MultiAgentDashboard } from "./features/multi-agent-dashboard";

type WorkspaceTab = "chat" | "agent-dashboard";

const TAB_COPY: Record<WorkspaceTab, { eyebrow: string; label: string; description: string }> = {
  chat: {
    eyebrow: "Default",
    label: "Agent Chat",
    description: "General-purpose Claude SDK workspace",
  },
  "agent-dashboard": {
    eyebrow: "Design",
    label: "Multi-Agent Dashboard",
    description: "High-fidelity orchestration workspace",
  },
};

export default function App() {
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("chat");

  useEffect(() => {
    if (activeTab === "agent-dashboard") {
      document.title = "Multi-Agent Dashboard — ClaudeSDK";
    }
  }, [activeTab]);

  return (
    <div className="workspace-app">
      <header className="workspace-tabbar">
        <div className="workspace-tabbar-copy">
          <span className="workspace-tabbar-label">Workspace tabs</span>
          <h1>ClaudeSDK Frontend</h1>
        </div>

        <nav className="workspace-tablist" aria-label="Feature workspaces">
          {(Object.keys(TAB_COPY) as WorkspaceTab[]).map((tab) => {
            const tabMeta = TAB_COPY[tab];
            const isActive = activeTab === tab;

            return (
              <button
                key={tab}
                className={`workspace-tab${isActive ? " is-active" : ""}`}
                type="button"
                aria-pressed={isActive}
                onClick={() => setActiveTab(tab)}
              >
                <span className="workspace-tab-eyebrow">{tabMeta.eyebrow}</span>
                <span className="workspace-tab-label">{tabMeta.label}</span>
                <span className="workspace-tab-description">{tabMeta.description}</span>
              </button>
            );
          })}
        </nav>
      </header>

      <main className="workspace-panels">
        <section className="workspace-panel" hidden={activeTab !== "chat"} aria-label="Agent chat workspace">
          <ChatContainer />
        </section>

        <section
          className="workspace-panel"
          hidden={activeTab !== "agent-dashboard"}
          aria-label="Multi-agent dashboard workspace"
        >
          <MultiAgentDashboard />
        </section>
      </main>
    </div>
  );
}
