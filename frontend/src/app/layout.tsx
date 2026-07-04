import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Halu Salud Ocupacional",
  description: "Sistema para IPS de salud ocupacional",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es-CO">
      <body>{children}</body>
    </html>
  );
}
