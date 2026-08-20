import BottomNavbar from '../components/navigation/BottomNavbar';

export default function AppLayout({ children }) {
    return (
        <>
            <div className="pb-16">{children}</div>
            <BottomNavbar />
        </>
    );
}
