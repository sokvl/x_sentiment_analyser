'use client';
import React from 'react';
import SentimentIndexChartTile from './SentimentIndexChartTile';

export default function SentimentIndexTwitterTile() {
    return (
        <SentimentIndexChartTile
            title="Sentiment Index — Twitter"
            endpoint="/api/signals/market-index/"
            seriesLabel="Twitter Sentiment"
        />
    );
}
