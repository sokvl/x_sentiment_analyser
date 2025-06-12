import './globals.css';
import BottomNavbar from './components/navigation/BottomNavbar';
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

                        <div className="pb-16">{children}</div>
                    <BottomNavbar />
                </body>
            </html>
        </UserConfigProvider>
    );
}
