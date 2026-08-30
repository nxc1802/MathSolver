import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { SWRProvider } from "@/lib/swr-provider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const viewport: Viewport = {
  themeColor: "#08090e",
  width: "device-width",
  initialScale: 1,
};

export const metadata: Metadata = {
  title: "MathSolver v5.1 — Agentic Visual Math & Geometry Platform",
  description: "Trợ lý giải toán hình học tương tác và mô phỏng 2D/3D đa tác tử với Manim Animation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="vi"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased dark`}
    >
      <body
        suppressHydrationWarning
        className="min-h-full flex flex-col bg-[var(--background)] text-[var(--foreground)] selection:bg-indigo-500/20 selection:text-indigo-200"
      >
        <AuthProvider>
          <SWRProvider>{children}</SWRProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
