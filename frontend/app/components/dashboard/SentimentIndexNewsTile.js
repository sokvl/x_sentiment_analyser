'use client';
import React from 'react';
import SentimentIndexChartTile from './SentimentIndexChartTile';

export default function SentimentIndexNewsTile() {
    return (
        <SentimentIndexChartTile
            title="Sentiment Index — News"
            endpoint="/api/news/finnhub/index/"
            seriesLabel="News Sentiment"
        />
    );
}
