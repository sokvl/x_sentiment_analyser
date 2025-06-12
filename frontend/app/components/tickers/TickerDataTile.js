'use client';
import React, { useState, useEffect } from 'react';
import Tile from '../common/Tile';
import { useUserConfig } from '../../utils/UserConfigContext';

export default function ProcessedTickerDataTile({ styles }) {
    const { state: userConfig, refreshConfig } = useUserConfig();
    const [tickerData, setTickerData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const processTickerData = (data) => {
        return Object.entries(data)
            .filter(([ticker, value]) => Array.isArray(value) && value.length > 0) // Filtruj poprawne dane (z co najmniej jednym wpisem)
            .map(([ticker, records]) => {
                const latestRecord = records[records.length - 1]; // Najnowsza data
                const openPrice = latestRecord[`Open ${ticker.replace('$', '')}`];
                const closePrice = latestRecord[`Close ${ticker.replace('$', '')}`];

                if (!openPrice || !closePrice) return null;

                const priceChange = ((closePrice - openPrice) / openPrice) * 100;

                return {
                    ticker: ticker.replace('$', ''),
                    date: latestRecord.Date.split('T')[0],
                    close: closePrice,
                    change: priceChange,
                };
            })
            .filter(Boolean);
    };

    // Funkcja do pobierania danych z API
    const fetchTickerData = async (tickers) => {
        if (!tickers || tickers.length === 0) {
            setTickerData([]);
            setLoading(false);
            return;
        }

        setLoading(true);
        setError(null);
        try {
            const tickerQuery = tickers.map((t) => `${t}`).join(',');
            const response = await fetch(`http://localhost:8000/api/tickers/stock-data/?tickers=${tickerQuery}`);

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            const data = await response.json();
            const processedData = processTickerData(data);
            setTickerData(processedData);
        } catch (err) {
            setError(`Error fetching data: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    // Pobieranie danych po załadowaniu komponentu
    useEffect(() => {
        if (userConfig.isLoaded && userConfig.tickers.length > 0) {
            fetchTickerData(userConfig.tickers);
        } else {
            setTickerData([]);
        }
    }, [userConfig]);

    return (
        <Tile className={`w-full  ${styles}`} >
            <h2 className="text-lg font-semibold mb-4 text-gray-200">Price Changes</h2>

            {loading ? (
                <p>Loading data...</p>
            ) : error ? (
                <p className="text-red-500">{error}</p>
            ) : tickerData.length > 0 ? (
                <div className="overflow-x-auto">
                    <table className="w-full text-sm border-collapse">
                        <thead>
                            <tr className="bg-gray-700 text-gray-300">
                                <th className="p-1 text-center font-semibold">Ticker</th>
                                <th className="p-1 text-center font-semibold">Date</th>
                                <th className="p-1 text-center font-semibold">Price</th>
                                <th className="p-1 text-center font-semibold">Change %</th>
                            </tr>
                        </thead>
                        <tbody>
                            {tickerData.map((row, index) => (
                                <tr
                                    key={index}
                                    className="border-t border-gray-700 hover:bg-gray-800"
                                >
                                    <td className="p-2 font-semibold text-gray-200">{row.ticker}</td>
                                    <td className="p-2 text-gray-300">{row.date}</td>
                                    <td className="p-2 text-gray-300">${row.close.toFixed(2)}</td>
                                    <td
                                        className={`p-2 font-semibold ${
                                            row.change > 0
                                                ? 'text-green-400'
                                                : row.change < 0
                                                ? 'text-red-400'
                                                : 'text-yellow-400'
                                        }`}
                                    >
                                        {row.change > 0 ? '⯅ ' : '⯆ '}
                                        {Math.abs(row.change.toFixed(2))}%
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ) : (
                <p className="text-gray-400 text-center py-4">No tickers observed.</p>
            )}

        </Tile>
    );
}
