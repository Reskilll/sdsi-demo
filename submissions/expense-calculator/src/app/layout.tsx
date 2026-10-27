import type { Metadata } from 'next';
import { ToastProvider } from '@/components/toast-provider';
import ToastContainer from '@/components/toast-container';
import './globals.css';

export const metadata: Metadata = {
  title: 'SplitSage — Smart Expense Splitter',
  description: 'Settle team outing expenses with minimum payments, auth, and history.',
  icons: {
    icon: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><text y="28" font-size="28">💰</text></svg>',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-surface antialiased">
        <ToastProvider>
          {children}
          <ToastContainer />
        </ToastProvider>
      </body>
    </html>
  );
}