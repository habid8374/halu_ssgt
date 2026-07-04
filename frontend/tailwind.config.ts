import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Semáforo del tablero de flujo (estados de Atencion).
        estado: {
          registrado: "#94a3b8",
          espera: "#f59e0b",
          llamado: "#3b82f6",
          atencion: "#8b5cf6",
          paraclinicos: "#06b6d4",
          finalizado: "#22c55e",
        },
      },
    },
  },
  plugins: [],
};

export default config;
