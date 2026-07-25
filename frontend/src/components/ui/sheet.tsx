"use client";

import * as React from "react"
import { motion, AnimatePresence } from "framer-motion"
import { X } from "lucide-react"

interface SheetContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
}

const SheetContext = React.createContext<SheetContextValue>({ open: false, setOpen: () => {} })

export function Sheet({ open, onOpenChange, children }: { open: boolean, onOpenChange: (open: boolean) => void, children: React.ReactNode }) {
  return <SheetContext.Provider value={{ open, setOpen: onOpenChange }}>{children}</SheetContext.Provider>
}

export function SheetContent({ children, className }: { children: React.ReactNode, className?: string }) {
  const { open, setOpen } = React.useContext(SheetContext)

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setOpen(false)}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
          />
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className={`fixed inset-y-0 right-0 z-50 w-full md:w-3/4 max-w-2xl border-l border-white/10 bg-background/95 p-6 shadow-2xl backdrop-blur-xl sm:max-w-sm ${className || ""}`}
          >
            <button
              onClick={() => setOpen(false)}
              className="absolute right-4 top-4 rounded-sm opacity-70 transition-opacity hover:opacity-100 focus:outline-none"
            >
              <X className="h-4 w-4" />
              <span className="sr-only">Close</span>
            </button>
            <div className="h-full overflow-y-auto pr-2 pb-6">
              {children}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

export function SheetHeader({ children, className }: { children: React.ReactNode, className?: string }) {
  return <div className={`flex flex-col space-y-2 text-center sm:text-left ${className || ""}`}>{children}</div>
}

export function SheetTitle({ children, className }: { children: React.ReactNode, className?: string }) {
  return <h2 className={`text-lg font-semibold text-foreground ${className || ""}`}>{children}</h2>
}
