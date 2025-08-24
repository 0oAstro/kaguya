import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Navbar } from "@/components/ui/navbar";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Kaguya - Live AI Mood Detection & Music",
  description: "Real-time mood detection through your camera with AI-powered music recommendations that match your current emotional state.",
  keywords: ["AI", "live mood detection", "camera", "real-time", "music", "playlist", "emotion analysis"],
  authors: [{ name: "Kaguya Team" }],
  icons: {
    icon: "/jigglypuff.png",
    shortcut: "/jigglypuff.png",
    apple: "/jigglypuff.png",
  },
  openGraph: {
    title: "Kaguya - Live AI Mood Detection & Music",
    description: "Real-time mood detection with AI-powered music recommendations",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <Navbar />
        {children}
      </body>
    </html>
  );
}
