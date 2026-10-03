import React, { createContext, useContext, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bookmark, Heart, Sparkles, Check, Info } from 'lucide-react';

export interface ToastItem {
  id: string;
  message: string;
  type?: 'success' | 'info' | 'gold';
  icon?: 'bookmark' | 'heart' | 'sparkles' | 'check' | 'info';
  duration?: number;
}

interface ToastContextType {
  showToast: (message: string, options?: Partial<Omit<ToastItem, 'id' | 'message'>>) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const showToast = useCallback((message: string, options?: Partial<Omit<ToastItem, 'id' | 'message'>>) => {
    const id = Math.random().toString(36).substring(2, 9);
    const newToast: ToastItem = {
      id,
      message,
      type: options?.type || 'gold',
      icon: options?.icon || 'check',
      duration: options?.duration || 3200,
    };

    setToasts((prev) => [...prev, newToast]);

    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, newToast.duration);
  }, []);

  const getIcon = (icon?: string) => {
    switch (icon) {
      case 'bookmark':
        return <Bookmark className="w-4 h-4 text-amber-500 fill-amber-500/20" />;
      case 'heart':
        return <Heart className="w-4 h-4 text-amber-500 fill-amber-500" />;
      case 'sparkles':
        return <Sparkles className="w-4 h-4 text-amber-400" />;
      case 'info':
        return <Info className="w-4 h-4 text-amber-400" />;
      default:
        return <Check className="w-4 h-4 text-amber-400" />;
    }
  };

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {/* Toast Notification Container in bottom-right corner as specified */}
      <div className="fixed bottom-8 right-8 z-50 flex flex-col gap-2 pointer-events-none max-w-sm w-full">
        <AnimatePresence>
          {toasts.map((toast) => (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.95 }}
              transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
              className="pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-xl bg-[#23252b]/95 border border-amber-500/30 backdrop-blur-md shadow-2xl text-slate-100 text-sm font-sans"
            >
              <div className="w-7 h-7 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center shrink-0">
                {getIcon(toast.icon)}
              </div>
              <span className="flex-1 font-medium text-xs sm:text-sm text-slate-100">{toast.message}</span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = (): ToastContextType => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};
