"use client";

import AppShell from "@/components/AppShell";
import EpidemiologiaPanel from "@/components/EpidemiologiaPanel";

export default function PortalEpidemiologiaPage() {
  return (
    <AppShell titulo="Diagnóstico de condiciones de salud">
      <EpidemiologiaPanel />
    </AppShell>
  );
}
