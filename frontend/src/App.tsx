import { useState } from "react";
import { AccountList } from "@/components/AccountList";
import { RateSchedule } from "@/components/RateSchedule";

type View = "accounts" | "rates";

/**
 * App — top-level layout with tab navigation.
 * All data fetching is handled by TanStack Query in child components.
 */
export default function App() {
  const [view, setView] = useState<View>("accounts");

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b px-6 py-4">
        <h1 className="text-xl font-semibold">nbus Ledger</h1>
      </header>

      {/* Tab navigation */}
      <nav className="border-b px-6">
        <div className="flex gap-4">
          {(["accounts", "rates"] as View[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setView(tab)}
              className={[
                "py-3 text-sm font-medium border-b-2 -mb-px transition-colors",
                view === tab
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              ].join(" ")}
            >
              {tab === "accounts" ? "Accounts" : "Rate Schedule"}
            </button>
          ))}
        </div>
      </nav>

      {/* Main content */}
      <main className="px-6 py-6 max-w-5xl mx-auto">
        {view === "accounts" && <AccountList />}
        {view === "rates" && <RateSchedule />}
      </main>
    </div>
  );
}
