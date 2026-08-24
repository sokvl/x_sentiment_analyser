'use client';
import React from 'react';
import Tile from '../common/Tile';

const NOVNC_URL = process.env.NEXT_PUBLIC_NOVNC_URL;
const VNC_PASSWORD = process.env.NEXT_PUBLIC_VNC_PASSWORD;

export default function ScraperLiveViewTile() {
    if (!NOVNC_URL) {
        return (
            <Tile>
                <h2 className="text-sm font-semibold mb-2 text-gray-200">Scraper Live View</h2>
                <p className="text-gray-400 text-xs">Live view is not configured.</p>
            </Tile>
        );
    }

    const src = `${NOVNC_URL}/?autoconnect=1&resize=scale&view_only=1&password=${encodeURIComponent(VNC_PASSWORD || '')}`;

    return (
        <Tile>
            <h2 className="text-sm font-semibold mb-2 text-gray-200">Scraper Live View</h2>
            <iframe
                src={src}
                className="w-full aspect-video rounded-md border border-gray-700 pointer-events-none"
                title="Scraper live browser view (read-only)"
            />
        </Tile>
    );
}
