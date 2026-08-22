'use client';
import React, { useEffect, useMemo, useState } from 'react';
import { Line } from 'react-chartjs-2';
import Tile from '../common/Tile';
import apiFetch from '../../utils/apiFetch';
import { registerChartElements } from '../../utils/chartConfig';
import { useUserConfig } from '../../utils/UserConfigContext';

const DAY_SPAN_OPTIONS = [7, 30, 90];

registerChartElements();

function buildIndexSeries(apiData) {
    const totalsByDate = {};

    for (const { predictions } of apiData) {
        for (const [date, counts] of Object.entries(predictions || {})) {
            if (!totalsByDate[date]) {
                totalsByDate[date] = { 0: 0, 1: 0, 2: 0 };
            }
            totalsByDate[date][0] += counts[0] || 0;
            totalsByDate[date][1] += counts[1] || 0;
            totalsByDate[date][2] += counts[2] || 0;
        }
    }

    const dates = Object.keys(totalsByDate).sort();
    const values = dates.map((date) => {
        const { 0: negative, 1: neutral, 2: positive } = totalsByDate[date];
        const total = negative + neutral + positive;
        return total > 0 ? Math.round(((positive - negative) / total) * 100) : 0;
    });

    return { dates, values };
}

export default function SentimentIndexTwitterTile() {
    const { state: userConfig } = useUserConfig();
    const [days, setDays] = useState(30);
    const [series, setSeries] = useState({ dates: [], values: [] });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const tickerQuery = useMemo(
        () => (userConfig.tickers || []).join(','),
        [userConfig.tickers]
    );

    useEffect(() => {
        if (!tickerQuery) {
            setSeries({ dates: [], values: [] });
            return;
        }

        const fetchIndex = async () => {
            setLoading(true);
            setError(null);
            try {
                const response = await apiFetch(
                    `/api/predictions-by-day/?tickers=${tickerQuery}&days=${days}`
                );
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                const data = await response.json();
                setSeries(buildIndexSeries(data));
            } catch (err) {
                setError(`Error fetching sentiment index: ${err.message}`);
            } finally {
                setLoading(false);
            }
        };

        fetchIndex();
    }, [tickerQuery, days]);

    const chartData = {
        labels: series.dates,
        datasets: [
            {
                label: 'Twitter Sentiment',
                data: series.values,
                borderColor: 'rgb(96, 165, 250)',
                backgroundColor: 'rgba(96, 165, 250, 0.2)',
                tension: 0.3,
                pointRadius: 0,
            },
        ],
    };

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            y: {
                min: -100,
                max: 100,
                ticks: { color: '#d1d5db', font: { size: 9 } },
                grid: { color: '#374151' },
            },
            x: {
                ticks: { display: false },
                grid: { color: '#374151' },
            },
        },
        plugins: {
            legend: { display: false },
        },
    };

    return (
        <Tile className="aspect-square flex flex-col">
            <div className="flex items-center justify-between mb-2">
                <h2 className="text-sm font-semibold text-gray-200">Sentiment Index — Twitter</h2>
                <select
                    value={days}
                    onChange={(e) => setDays(Number(e.target.value))}
                    className="px-1 py-0.5 rounded bg-gray-700 text-gray-200 border border-gray-600 text-[11px]"
                >
                    {DAY_SPAN_OPTIONS.map((option) => (
                        <option key={option} value={option}>
                            {option}d
                        </option>
                    ))}
                </select>
            </div>

            <div className="flex-1 min-h-0">
                {loading ? (
                    <p className="text-gray-400 text-xs">Loading...</p>
                ) : error ? (
                    <p className="text-red-400 text-xs">{error}</p>
                ) : series.dates.length > 0 ? (
                    <Line data={chartData} options={chartOptions} />
                ) : (
                    <p className="text-gray-400 text-xs">No data available.</p>
                )}
            </div>
        </Tile>
    );
}
