import { useEffect } from "react";
import Composer from "./components/Composer";
import EventStream from "./components/EventStream";
import PreviewPane from "./components/PreviewPane";
import Sidebar from "./components/Sidebar";
import StatusBar from "./components/StatusBar";
import TerminalPane from "./components/TerminalPane";
import TopBar from "./components/TopBar";
import { useOmi } from "./state/store";

export default function App() {
  const refreshTasks = useOmi((s) => s.refreshTasks);
  useEffect(() => {
    void refreshTasks();
    const t = setInterval(() => void useOmi.getState().refreshTasks(), 15000);
    return () => clearInterval(t);
  }, [refreshTasks]);

  return (
    <div className="h-full flex flex-col">
      <TopBar />
      <div className="flex-1 grid grid-cols-[270px_1fr_340px] min-h-0 gap-2 p-2">
        <Sidebar />
        <main className="flex flex-col min-h-0 gap-2">
          <EventStream />
          <Composer />
        </main>
        <aside className="flex flex-col min-h-0 gap-2">
          <TerminalPane />
          <PreviewPane />
        </aside>
      </div>
      <StatusBar />
    </div>
  );
}
