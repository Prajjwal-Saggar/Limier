import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/Nav";
import { SmoothScroll } from "@/components/SmoothScroll";

export const metadata: Metadata = {
  title: "Limier - AI-Powered AML Investigation",
  description: "An AI-powered anti-money laundering compliance dashboard.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased min-h-screen flex flex-col relative selection:bg-primary/30 selection:text-primary">
        {/* Subtle background glow effect */}
        <div className="fixed inset-0 pointer-events-none z-[-1] overflow-hidden">
          <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] rounded-full bg-primary/10 blur-[150px]" />
          <div className="absolute top-[40%] right-[-10%] w-[40%] h-[50%] rounded-full bg-primary/5 blur-[120px]" />
        </div>
        
        <SmoothScroll>
          <Nav />
          <main className="flex-1 pt-16">
            {children}
          </main>
          
          <footer className="w-full border-t border-white/5 bg-black/40 backdrop-blur-md py-6 mt-16 text-center">
            <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row justify-between items-center gap-4 text-xs text-muted-foreground/60">
              <span className="font-display font-medium text-muted-foreground/80">Limier — AI-Powered AML Investigation</span>
              <span>Hackathon demo environment. No real customer data.</span>
            </div>
          </footer>
        </SmoothScroll>
      </body>
    </html>
  );
}
