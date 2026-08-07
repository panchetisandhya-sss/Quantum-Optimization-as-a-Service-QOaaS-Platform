import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "QOaaS - Enterprise Quantum Optimization-as-a-Service",
  description: "Solve complex business optimization problems using hybrid quantum-classical solvers without coding.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link 
          rel="stylesheet" 
          href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css" 
          crossOrigin="anonymous" 
        />
        <script 
          defer 
          src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js" 
          crossOrigin="anonymous" 
        ></script>
        <script 
          defer 
          src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js" 
          crossOrigin="anonymous" 
        ></script>
        <script 
          defer 
          src="https://cdn.jsdelivr.net/npm/qrcode@1.5.3/build/qrcode.min.js" 
          crossOrigin="anonymous" 
        ></script>
      </head>
      <body className="antialiased">
        <div className="min-h-screen bg-grid-pattern bg-repeat relative">
          {/* Subtle Ambient Background Gradients */}
          <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-quantum-blue/10 blur-[150px] pointer-events-none" />
          <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-quantum-purple/10 blur-[150px] pointer-events-none" />
          {children}
        </div>
      </body>
    </html>
  );
}
