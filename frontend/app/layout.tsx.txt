export const metadata = {
  title: 'KalyanX',
  description: 'AI-powered prediction platform',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
