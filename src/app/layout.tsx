import type { Metadata } from "next";
import { Urbanist } from "next/font/google";
import "./globals.css";

// Configure Urbanist font for regular text
const urbanist = Urbanist({
  variable: "--font-urbanist",
  subsets: ["latin"],
  weight: ["100", "200", "300", "400", "500", "600", "700", "800", "900"], // All weights Urbanist supports
});

// Metadata remains the same
export const metadata: Metadata = {
  title: "Robin",
  description: "Rediscover the Joy of the Open Road",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${urbanist.variable} antialiased`}>    
        {children}
      </body>
    </html>
  );
}