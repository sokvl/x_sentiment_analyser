'use client'
import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faTachometerAlt, faChartBar, faCogs, faDisplay } from '@fortawesome/free-solid-svg-icons';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function BottomNavbar() {
    const pathname = usePathname(); // Pobiera aktywną ścieżkę URL

    const tabs = [
        { name: 'Dashboard', href: '/', icon: faTachometerAlt },
        { name: 'Benchmark', href: '/benchmark', icon: faChartBar },
        { name: 'Setup', href: '/setup', icon: faDisplay },
        { name: 'Config', href: '/config', icon: faCogs },
    ];

    return (
        <nav className="fixed bottom-0 left-0 w-full bg-gray-900 shadow-lg">
            <ul className="flex justify-start gap-1 pr-2">
                {tabs.map((tab) => (
                    <li key={tab.name} className="flex">
                        <Link href={tab.href}>
                            <div
                                className={`relative px-4 py-1.5 flex items-center gap-2 text-xs cursor-pointer
                                ${
                                    pathname === tab.href
                                        ? 'bg-gray-800 text-white'
                                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                                }`}
                                style={{
                                    clipPath:
                                        'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0% 100%)',
                                }}
                            >
                                <FontAwesomeIcon icon={tab.icon} size="sm" />
                                <span>{tab.name}</span>
                            </div>
                        </Link>
                    </li>
                ))}
            </ul>
        </nav>
    );
}
