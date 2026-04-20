import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Seasonal Color Analysis",
  description: "CV-based seasonal color estimate"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
