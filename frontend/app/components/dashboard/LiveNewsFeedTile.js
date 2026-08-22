'use client';
import React from 'react';
import Tile from '../common/Tile';

const MOCK_NEWS = [
    {
        id: 1,
        ticker: '$TSLA',
        source: 'Reuters',
        headline: 'Tesla deliveries beat estimates as demand rebounds in key markets',
        timeLabel: '12m ago',
    },
    {
        id: 2,
        ticker: '$AAPL',
        source: 'Bloomberg',
        headline: 'Apple suppliers ramp up production ahead of holiday season',
        timeLabel: '47m ago',
    },
    {
        id: 3,
        ticker: '$NVDA',
        source: 'CNBC',
        headline: 'Nvidia announces next-gen chip amid soaring AI demand',
        timeLabel: '1h 30m ago',
    },
    {
        id: 4,
        ticker: '$TSLA',
        source: 'MarketWatch',
        headline: 'Analysts split on Tesla outlook following earnings call',
        timeLabel: '2h 30m ago',
    },
];

export default function LiveNewsFeedTile() {
    return (
        <Tile>
            <div className="flex items-center justify-between mb-2">
                <h2 className="text-sm font-semibold text-gray-200">Live Feed — News</h2>
                <span className="text-[10px] text-gray-500 uppercase">Mock data</span>
            </div>

            <div className="space-y-1.5 max-h-48 overflow-y-auto">
                {MOCK_NEWS.map((item) => (
                    <div key={item.id} className="bg-gray-700 rounded-md p-1.5 text-xs">
                        <div className="flex justify-between items-center text-[11px] text-gray-400 mb-0.5">
                            <div className="flex items-center gap-1.5">
                                <span className="font-semibold text-blue-400">{item.ticker}</span>
                                <span className="text-gray-500">{item.source}</span>
                            </div>
                            <span>{item.timeLabel}</span>
                        </div>
                        <p className="text-gray-200">{item.headline}</p>
                    </div>
                ))}
            </div>
        </Tile>
    );
}
