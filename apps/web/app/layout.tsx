import type { Metadata } from "next";
import { Cormorant_Garamond, Manrope } from "next/font/google";
import "./globals.css";

const bodySans = Manrope({
  subsets: ["latin"],
  variable: "--font-body"
});

const headingSerif = Cormorant_Garamond({
  subsets: ["latin"],
  variable: "--font-heading",
  weight: ["500", "600", "700"]
});

export const metadata: Metadata = {
  title: "Seasonal Color Studio",
  description: "Editorial-style seasonal color analysis with clear, practical guidance"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${bodySans.variable} ${headingSerif.variable} app-shell`}>
        <div className="ambient" aria-hidden="true">
          <span className="blob blob-blush" />
          <span className="blob blob-lilac" />
          <span className="blob blob-butter" />
          <span className="spark spark-one" />
          <span className="spark spark-two" />
        </div>
        {children}
      </body>
    </html>
  );
}
