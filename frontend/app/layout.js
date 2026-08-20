import './globals.css';
import { UserConfigProvider } from './utils/UserConfigContext'; // Zaimportuj context

export const metadata = {
    title: 'Stock NLP App',
    description: 'Stock Market Analysis',
};

export default function RootLayout({ children }) {
    return (
        <UserConfigProvider>
            <html lang="en">
                <body className="bg-gray-900 text-gray-200 font-dm-mono">
                    {children}
                </body>
            </html>
        </UserConfigProvider>
    );
}
