'use client';
import React from 'react';
import Tile from '../common/Tile';

export default function LiveNewsFeedTile() {
    return (
        <Tile>
            <h2 className="text-sm font-semibold mb-2 text-gray-200">Live Feed — News</h2>
            <div className="max-h-48 flex items-center justify-center">
                <p className="text-gray-400 text-xs">Coming soon.</p>
            </div>
        </Tile>
    );
}
