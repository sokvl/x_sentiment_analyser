'use client';
import React from 'react';

export const SENTIMENT_LABELS = { 0: 'Negative', 1: 'Neutral', 2: 'Positive' };
export const SENTIMENT_COLORS = { 0: 'text-red-400', 1: 'text-yellow-400', 2: 'text-green-400' };

export default function SentimentTag({ prediction, probabilities }) {
    if (prediction === null || prediction === undefined) return null;

    return (
        <>
            <span className={`font-semibold ${SENTIMENT_COLORS[prediction] ?? 'text-gray-400'}`}>
                {SENTIMENT_LABELS[prediction] ?? 'Unknown'}
            </span>
            {probabilities && (
                <span className="text-gray-500">
                    [{probabilities.map((p) => p.toFixed(2)).join(', ')}]
                </span>
            )}
        </>
    );
}
