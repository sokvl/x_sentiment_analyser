'use client';
import React, { useEffect, useState } from 'react';
import { Line } from 'react-chartjs-2';
import Tile from '../common/Tile';
import apiFetch from '../../utils/apiFetch';
import { registerChartElements } from '../../utils/chartConfig';

const DAY_SPAN_OPTIONS = [7, 30, 90];

registerChartElements();

function toDateString(date) {
    return date.toISOString().split('T')[0];
}

export default function SentimentIndexChartTile({ title, endpoint, seriesLabel }) {
    const [days, setDays] = useState(30);
    const [series, setSeries] = useState({ dates: [], values: [] });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchIndex = async () => {
            setLoading(true);
            setError(null);
            try {
                const endDate = new Date();
                const startDate = new Date(endDate.getTime() - days * 24 * 60 * 60 * 1000);
                const response = await apiFetch(
                    `${endpoint}?start_date=${toDateString(startDate)}&end_date=${toDateString(endDate)}`
                );
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                const data = await response.json();
                const dates = (data.series || []).map((point) => point.date);
                const values = (data.series || []).map((point) => point.index);
                setSeries({ dates, values });
            } catch (err) {
                setError(`Error fetching sentiment index: ${err.message}`);
            } finally {
                setLoading(false);
            }
        };

        fetchIndex();
    }, [endpoint, days]);

    const chartData = {
        labels: series.dates,
        datasets: [
            {
                label: seriesLabel,
                data: series.values,
                borderColor: 'rgb(96, 165, 250)',
                backgroundColor: 'rgba(96, 165, 250, 0.2)',
                tension: 0,
                pointRadius: 3,
                pointBackgroundColor: 'rgb(96, 165, 250)',
            },
        ],
    };

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            y: {
                min: -1,
                max: 1,
                ticks: { color: '#d1d5db', font: { size: 9 }, stepSize: 0.5 },
                grid: { color: '#374151' },
            },
            x: {
                ticks: {
                    color: '#d1d5db',
                    font: { size: 8 },
                    maxRotation: 45,
                    minRotation: 45,
                    autoSkip: true,
                    maxTicksLimit: 6,
                },
                grid: { color: '#374151' },
            },
        },
        plugins: {
            legend: { display: false },
            tooltip: {
                callbacks: {
                    label: (context) => `Index: ${context.parsed.y}`,
                },
            },
        },
    };

    return (
        <Tile className="aspect-square flex flex-col">
            <div className="flex items-center justify-between mb-2">
                <h2 className="text-sm font-semibold text-gray-200">{title}</h2>
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

            <div className="flex-1 min-h-0 relative">
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
