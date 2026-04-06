import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Make it Move',
  description: 'Online PK vs Agent'
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
