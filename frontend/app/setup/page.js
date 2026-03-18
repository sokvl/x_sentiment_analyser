'use client';
import React, { useState, useEffect } from 'react';
import ScraperStatusTile from '../components/scraper/ScraperStatusTile';
import TickersTile from '../components/tickers/TickersTile';
import SignalForecastTile from '../components/signals/SignalForecastTile';
import { useUserConfig } from '../utils/UserConfigContext';

export default function SetupPage() {
    const { state: userConfig } = useUserConfig();
    const [availableTickers, setAvailableTickers] = useState([]);
    const [observedTickers, setObservedTickers] = useState([]);
    const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
    const [signalProps, setSignalProps] = useState(null);
    const [loading, setLoading] = useState(false);
    const [alert, setAlert] = useState(null);
    const [error, setError] = useState(null);

    const startScraper = async () => {
        setLoading(true);
        setAlert(null);
        try {
            const response = await fetch('http://localhost:8000/api/scraper/start/', {
                method: 'POST',
            });
            if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
            const data = await response.json();
            setAlert({ type: 'success', message: data.message || 'Scraper started successfully!' });
        } catch (err) {
            setAlert({ type: 'error', message: `Error: ${err.message}` });
        } finally {
            setLoading(false);
        }
    };

    const fetchTickers = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/tickers/tickers/');
            if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
            const data = await response.json();
            // Ensure we always store an array
            setAvailableTickers(Array.isArray(data) ? data : data?.results ?? []);
        } catch (err) {
            setError(`Error fetching tickers: ${err.message}`);
            setAvailableTickers([]);
        }
    };

    useEffect(() => {
        fetchTickers();
    }, []);

    useEffect(() => {
        const configTickers = Array.isArray(userConfig?.tickers) ? userConfig.tickers : [];
        const safeTickers = Array.isArray(availableTickers) ? availableTickers : [];

        if (configTickers.length > 0) {
            const initialObservedTickers = configTickers.map((ticker) => ({
                symbol: `$${ticker}`,
                full_name: safeTickers.find(
                    (t) => t.symbol?.replace(/^\$/, '') === ticker
                )?.full_name || '',
            }));
            setObservedTickers(initialObservedTickers);
        }
    }, [userConfig, availableTickers]);

    const handleGenerateSignals = () => {
        const tickersWithoutDollar = Array.isArray(observedTickers)
            ? observedTickers.map((ticker) => ticker.symbol.replace(/^\$/, ''))
            : [];
        setSignalProps({ date: selectedDate, tickers: tickersWithoutDollar });
    };

    return (
        <main className="p-8 bg-gray-900 min-h-screen text-gray-200">
            <h1 className="text-3xl font-bold mb-6">Setup</h1>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="max-w-full w-full">
                    <div className="p-4 bg-gray-800 rounded-lg shadow-lg h-full">
                        <ScraperStatusTile
                            status="IDLE"
                            website="x.com"
                            ticker="$TSLA"
                            tweetCount={100}
                            showStartButton={true}
                        />
                        {alert && (
                            <div
                                className={`mt-4 p-4 rounded-md text-sm ${
                                    alert.type === 'success'
                                        ? 'bg-green-700 text-green-100'
                                        : 'bg-red-700 text-red-100'
                                }`}
                            >
                                {alert.message}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {signalProps && (
                <div className="mt-6">
                    <SignalForecastTile date={signalProps.date} tickers={signalProps.tickers} />
                </div>
            )}

            <div className="mt-6 p-4 bg-gray-800 rounded-lg shadow-lg">
                <h2 className="p-3 text-xl font-semibold text-gray-200">Generate Signals</h2>

                <div className="p-3">
                    <label htmlFor="date" className="block text-sm font-medium text-gray-300">
                        Select Date
                    </label>
                    <input
                        type="date"
                        id="date"
                        value={selectedDate}
                        onChange={(e) => setSelectedDate(e.target.value)}
                        className="mt-1 block w-full px-4 py-2 bg-gray-800 border border-gray-600 rounded-md text-gray-200 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    />
                </div>

                <div className="mb-4">
                    <TickersTile
                        availableTickers={availableTickers}
                        observedTickersProp={observedTickers}
                        onObservedTickersChange={(updatedTickers) => setObservedTickers(updatedTickers)}
                    />
                </div>

                <button
                    onClick={handleGenerateSignals}
                    className="w-full bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
                >
                    Generate Signals
                </button>
            </div>
        </main>
    );
}