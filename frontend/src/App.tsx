import React, { useEffect } from 'react';
import { HeaderBar } from './components/shell/HeaderBar';
import { FooterBar } from './components/shell/FooterBar';
import { WellLogInputPanel } from './components/upload/WellLogInputPanel';
import { GeologistAssistantPanel } from './components/chat/GeologistAssistantPanel';
import { WellLogPlotPanel } from './components/wellog/WellLogPlotPanel';
import { useSessionStore } from './stores/sessionStore';

export function App() {
  const bootstrap = useSessionStore((s) => s.bootstrap);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  return (
    <div className="w-screen h-screen min-h-screen bg-[#1c1409] flex flex-col overflow-hidden font-mono text-[#e8ddc7] cyber-grid-bg select-none">
      {/* Cyber Scanline Overlay */}
      <div className="pointer-events-none absolute inset-0 z-50 cyber-scanline opacity-30" />

      {/* Top Header Bar */}
      <HeaderBar />

      {/* Main Full-Viewport 3-Column Cyberpunk HUD Console */}
      <main className="flex-1 grid grid-cols-1 md:grid-cols-[280px_minmax(0,1fr)_460px] overflow-hidden gap-[2px] bg-[#4a3813] relative z-10">
        {/* Section 01: Well Log Input */}
        <section className="bg-[#1c1409] h-full overflow-y-auto">
          <WellLogInputPanel />
        </section>

        {/* Section 02: Geologist AI Core Console */}
        <section className="bg-[#1c1409] h-full flex flex-col overflow-hidden">
          <GeologistAssistantPanel />
        </section>

        {/* Section 03: Subsurface Curve Telemetry */}
        <section className="bg-[#1c1409] h-full overflow-y-auto">
          <WellLogPlotPanel />
        </section>
      </main>

      {/* Bottom Telemetry Footer */}
      <FooterBar />
    </div>
  );
}

export default App;
