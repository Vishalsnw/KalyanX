export const metadata = {
  title: 'KalyanX',
  description: 'Satta prediction app',
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
