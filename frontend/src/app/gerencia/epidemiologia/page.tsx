"use client";

import AppShell from "@/components/AppShell";
import EpidemiologiaPanel from "@/components/EpidemiologiaPanel";

export default function GerenciaEpidemiologiaPage() {
  return (
    <AppShell titulo="Epidemiología (condiciones de salud)">
      <EpidemiologiaPanel conEmpresa />
    </AppShell>
  );
}
