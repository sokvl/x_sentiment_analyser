'use client';
import React from 'react';
import Tile from '../common/Tile';

export default function SentimentIndexNewsTile() {
    return (
        <Tile className="aspect-square flex flex-col">
            <h2 className="text-sm font-semibold text-gray-200 mb-2">Sentiment Index — News</h2>
            <div className="flex-1 flex items-center justify-center">
                <p className="text-gray-400 text-xs">Coming soon.</p>
            </div>
        </Tile>
    );
}
