import React, { useEffect } from 'react';
import { HeaderBar } from './components/shell/HeaderBar';
import { FooterBar } from './components/shell/FooterBar';
import { DesktopOnlyNotice } from './components/shell/DesktopOnlyNotice';
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
      <div className="hidden xl:block shrink-0">
        <HeaderBar />
      </div>

      {/* Below 1280px the console is withheld -- see DesktopOnlyNotice. */}
      <DesktopOnlyNotice />

      {/* Main Full-Viewport 3-Column Cyberpunk HUD Console */}
      {/* 20 / 50 / 30. Wider flanks are worth the narrower chat column. */}
      <main className="hidden xl:grid flex-1 grid-cols-[minmax(0,1fr)_minmax(0,2.5fr)_minmax(0,1.5fr)] overflow-hidden gap-[2px] bg-[#4a3813] relative z-10">
        {/* Section 01: Well Log Input */}
        <section className="bg-[#1c1409] h-full min-h-0 overflow-hidden">
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
      <div className="hidden xl:block shrink-0">
        <FooterBar />
      </div>
    </div>
  );
}

export default App;
