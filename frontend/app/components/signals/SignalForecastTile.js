'use client';
import React, { useState, useEffect } from 'react';
import Tile from '../common/Tile';
import { useUserConfig } from '../../utils/UserConfigContext';

export default function SignalForecastTile({ date = new Date().toISOString().split('T')[0], tickers }) {
    const { state: userConfig } = useUserConfig();
    const [signals, setSignals] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const fetchSignals = async () => {
        if (!tickers || tickers.length === 0) {
            console.log('No tickers to fetch signals for.');
            setSignals([]);
            return;
        }

        setLoading(true);
        setError(null);
        try {
            const { config_id, used_model } = userConfig;
            const tickerQuery = tickers.join(',');
            console.log(`Fetching signals for: ${tickerQuery} on ${date} (model: ${used_model}, config: ${config_id})`);

            const response = await fetch(
                `http://localhost:8000/api/signals/generate/?date=${date}&tickers=${tickerQuery}&used_model=${used_model}&config_id=${config_id}&with_save=false`
            );

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status} - ${response.statusText}`);
            }

            const data = await response.json();

            // data is a dictionary where keys are tickers, convert to array for mapping
            const processedData = Object.values(data).map((item) => {
                let signal = 'HOLD';
                const sentiment = parseFloat(item.confidence_score); // Backend uses confidence_score
                if (!isNaN(sentiment)) {
                    if (sentiment > 0.1) signal = 'BUY';
                    else if (sentiment < -0.1) signal = 'SELL';
                }
                return {
                    ticker: item.ticker,
                    sentiment: isNaN(sentiment) ? 'N/A' : sentiment.toFixed(2),
                    signal,
                };
            });

            setSignals(processedData);
        } catch (err) {
            setError(`Error fetching signals: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (tickers?.length > 0) {
            fetchSignals();
        } else {
            setSignals([]);
        }
    }, [tickers, date]);

    return (
        <Tile className="w-full">
            <h2 className="text-lg font-semibold mb-4 text-gray-200">Signal Forecast</h2>

            {loading ? (
                <div className="text-gray-400 text-center py-4">Loading signals...</div>
            ) : error ? (
                <p className="text-red-500">Error: {error}</p>
            ) : signals.length > 0 ? (
                <div className="overflow-x-auto">
                    <table className="w-full text-sm border-collapse">
                        <thead>
                            <tr className="bg-gray-700 text-gray-300">
                                <th className="p-1 pl-2 text-left font-semibold">Ticker</th>
                                <th className="p-1 pl-2 text-left font-semibold">Sentiment</th>
                                <th className="p-1 pl-2 text-left font-semibold">Signal</th>
                            </tr>
                        </thead>
                        <tbody>
                            {signals.map((row, index) => (
                                <tr
                                    key={index}
                                    className={`border-t border-gray-700 hover:bg-gray-800`}
                                >
                                    <td className="p-2 font-semibold text-gray-200">{row.ticker}</td>
                                    <td className="p-2 text-gray-300">{row.sentiment}</td>
                                    <td
                                        className={`p-2 font-semibold ${row.signal === 'BUY'
                                                ? 'text-green-400'
                                                : row.signal === 'SELL'
                                                    ? 'text-red-400'
                                                    : 'text-yellow-400'
                                            }`}
                                    >
                                        {row.signal}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ) : (
                <div className="text-gray-400 text-center py-4">No tickers observed.</div>
            )}
        </Tile>
    );
}
