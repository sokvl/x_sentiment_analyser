'use client';
import React, { useEffect, useState } from 'react';
import Tile from '../common/Tile';
import apiFetch from '../../utils/apiFetch';
import { useUserConfig } from '../../utils/UserConfigContext';

function toDateString(date) {
    return date.toISOString().split('T')[0];
}

function addDays(dateString, days) {
    const date = new Date(dateString);
    date.setDate(date.getDate() + days);
    return date;
}

function buildPresetsFromBounds(startDate, endDate) {
    const start = new Date(startDate);
    const end = new Date(endDate);

    const recentWeekStart = addDays(endDate, -7) < start ? start : addDays(endDate, -7);
    const recentMonthStart = addDays(endDate, -30) < start ? start : addDays(endDate, -30);

    const presets = [
        { label: 'Most Recent Week', start: toDateString(recentWeekStart), end: toDateString(end) },
        { label: 'Most Recent Month', start: toDateString(recentMonthStart), end: toDateString(end) },
        { label: 'Full Available Range', start: toDateString(start), end: toDateString(end) },
    ];

    // De-duplicate presets that collapse to the same range when data is sparse.
    const seen = new Set();
    return presets.filter((preset) => {
        const key = `${preset.start}_${preset.end}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
    });
}

export default function PredictionReportTile() {
    const { state: userConfig } = useUserConfig();
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');
    const [tickers, setTickers] = useState('');
    const [reportData, setReportData] = useState(null);
    const [activeTicker, setActiveTicker] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const [presets, setPresets] = useState([]);
    const [presetsError, setPresetsError] = useState(null);

    const watchlistTickers = (userConfig.tickers || []).join(',');

    useEffect(() => {
        const fetchDataBounds = async () => {
            try {
                const response = await apiFetch('/api/signals/market-index/');
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                const data = await response.json();
                if (data.start_date && data.end_date) {
                    setPresets(buildPresetsFromBounds(data.start_date, data.end_date));
                }
            } catch (err) {
                setPresetsError(`Error loading available data range: ${err.message}`);
            }
        };

        fetchDataBounds();
    }, []);

    const runReport = async (queryTickers, queryStartDate, queryEndDate) => {
        setLoading(true);
        setError(null);
        try {
            const response = await apiFetch(
                `/api/signals/prediction-report/?start_date=${queryStartDate}&end_date=${queryEndDate}&tickers=${queryTickers}`
            );
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const data = await response.json();
            setReportData(data);
            // As long as there's at least one valid ticker, set it as active
            const firstTicker = Object.keys(data).find((key) => key !== 'total_correct');
            setActiveTicker(firstTicker);
        } catch (err) {
            setError(`Error fetching report: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    const fetchPredictionReport = (e) => {
        e.preventDefault();
        runReport(tickers, startDate, endDate);
    };

    const fetchPresetReport = (preset) => {
        runReport(watchlistTickers, preset.start, preset.end);
    };

    return (
        <Tile>
            <h2 className="text-lg font-semibold mb-4 text-gray-200">Prediction Report</h2>

            {/* Example presets — real watchlist tickers, date ranges backed by actual data */}
            {presetsError ? (
                <p className="text-yellow-500 text-sm mb-4">{presetsError}</p>
            ) : watchlistTickers && presets.length > 0 ? (
                <div className="mb-4">
                    <p className="text-sm text-gray-400 mb-2">
                        Quick presets — using your watchlist: {watchlistTickers}
                    </p>
                    <div className="flex flex-wrap gap-2">
                        {presets.map((preset) => (
                            <button
                                key={preset.label}
                                onClick={() => fetchPresetReport(preset)}
                                disabled={loading}
                                title={`${preset.start} to ${preset.end}`}
                                className={`px-3 py-1.5 rounded-md bg-gray-700 text-gray-200 text-sm ${
                                    loading ? 'opacity-50 cursor-not-allowed' : 'hover:bg-gray-600'
                                }`}
                            >
                                {preset.label}
                            </button>
                        ))}
                    </div>
                </div>
            ) : null}

            {/* Form */}
            <form onSubmit={fetchPredictionReport} className="mb-4 space-y-4">
                <div>
                    <label htmlFor="tickers" className="block text-sm font-medium text-gray-300">
                        Tickers (comma-separated)
                    </label>
                    <input
                        type="text"
                        id="tickers"
                        value={tickers}
                        onChange={(e) => setTickers(e.target.value)}
                        placeholder="$TSLA,$AAPL"
                        className="mt-1 block w-full px-4 py-2 bg-gray-800 border border-gray-600 rounded-md text-gray-200 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        required
                    />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                        <label htmlFor="startDate" className="block text-sm font-medium text-gray-300">
                            Start Date
                        </label>
                        <input
                            type="date"
                            id="startDate"
                            value={startDate}
                            onChange={(e) => setStartDate(e.target.value)}
                            className="mt-1 block w-full px-4 py-2 bg-gray-800 border border-gray-600 rounded-md text-gray-200 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                            required
                        />
                    </div>
                    <div>
                        <label htmlFor="endDate" className="block text-sm font-medium text-gray-300">
                            End Date
                        </label>
                        <input
                            type="date"
                            id="endDate"
                            value={endDate}
                            onChange={(e) => setEndDate(e.target.value)}
                            className="mt-1 block w-full px-4 py-2 bg-gray-800 border border-gray-600 rounded-md text-gray-200 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                            required
                        />
                    </div>
                </div>

                <button
                    type="submit"
                    disabled={loading}
                    className={`w-full px-4 py-2 rounded-md bg-blue-600 text-white ${
                        loading ? 'opacity-50 cursor-not-allowed' : 'hover:bg-blue-700'
                    }`}
                >
                    {loading ? 'Fetching...' : 'Generate Report'}
                </button>
            </form>

            {error && <p className="text-red-400">{error}</p>}

            {reportData && (
                <div className="mb-4 flex gap-4 border-b border-gray-700">
                    {Object.keys(reportData)
                        .filter((ticker) => ticker !== 'total_correct')
                        .map((ticker) => (
                            <button
                                key={ticker}
                                onClick={() => setActiveTicker(ticker)}
                                className={`px-4 py-2 text-sm font-semibold ${
                                    activeTicker === ticker
                                        ? 'border-b-2 border-blue-500 text-blue-400'
                                        : 'text-gray-400 hover:text-gray-200'
                                }`}
                            >
                                {ticker}
                            </button>
                        ))}
                </div>
            )}

            {/* Table for the active ticker */}
            {activeTicker && reportData[activeTicker] && (
                <div className="overflow-x-auto">
                    <h3 className="text-lg font-semibold text-gray-300 mt-4">
                        {activeTicker} Report
                    </h3>

                    <table className="w-full text-sm border-collapse mt-4">
                        <thead>
                            <tr className="bg-gray-700 text-gray-300">
                                <th className="p-2 text-left font-semibold">Date</th>
                                <th className="p-2 text-left font-semibold">Prediction</th>
                                <th className="p-2 text-left font-semibold">Actual Change (%)</th>
                                <th className="p-2 text-left font-semibold">Tweet Count</th>
                                <th className="p-2 text-left font-semibold">Correct?</th>
                            </tr>
                        </thead>
                        <tbody>
                            {Object.entries(reportData[activeTicker])
                                .filter(([date, data]) => !data.error && date !== 'ticker_total_correctness')
                                .map(([date, data], index) => (
                                    <tr
                                        key={`${activeTicker}-${date}-${index}`}
                                        className="border-t border-gray-700 hover:bg-gray-800"
                                    >
                                        <td className="p-2 text-gray-300">{date}</td>
                                        <td className="p-2 text-gray-300">{data.prediction}</td>
                                        <td className="p-2 text-gray-300">
                                            {data.actual_change?.toFixed(2)}%
                                        </td>
                                        <td className="p-2 text-gray-300">{data.tweet_count}</td>
                                        <td
                                            className={`p-2 font-semibold ${
                                                data.correct ? 'text-green-400' : 'text-red-400'
                                            }`}
                                        >
                                            {data.correct ? 'Yes' : 'No'}
                                        </td>
                                    </tr>
                                ))}
                        </tbody>
                    </table>

                    {/* Show the ticker-level correctness (if present) */}
                    <h4 className="mt-4 text-gray-200">
                        <strong>Total Correctness:</strong>{' '}
                        {reportData[activeTicker].ticker_total_correctness || 'N/A'}
                    </h4>
                </div>
            )}

            {/* Optionally show the overall correctness across ALL requested tickers, if desired */}
            {reportData?.total_correct && (
                <div className="mt-4 text-gray-200">
                    <strong>Overall correctness (all tickers):</strong> {reportData.total_correct}
                </div>
            )}
        </Tile>
    );
}
