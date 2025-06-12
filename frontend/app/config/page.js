'use client';

import React, { useState, useEffect } from 'react';
import ConfigTile from '../components/config/ConfigTile';
import TickersTile from '../components/tickers/TickersTile';
import JsonEditor from '../components/config/JsonEditor';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSave } from '@fortawesome/free-solid-svg-icons';

export default function Config() {
    const [config, setConfig] = useState(null);
    const [availableTickers, setAvailableTickers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isJsonEditorMode, setIsJsonEditorMode] = useState(false);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [modalMessage, setModalMessage] = useState('');

    const fetchConfig = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/config/?active=1');
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const data = await response.json();
            setConfig(data[0]);
        } catch (err) {
            setError(`Error fetching configuration: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    const fetchTickers = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/tickers/tickers/');
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const data = await response.json();
            setAvailableTickers(data);
        } catch (err) {
            setError(`Error fetching tickers: ${err.message}`);
        }
    };

    useEffect(() => {
        fetchConfig();
        fetchTickers();
    }, []);

    const formatDate = (dateString) => {
        return new Date(dateString).toLocaleString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    const updateConfigField = (field, value) => {
        setConfig((prevConfig) => ({
            ...prevConfig,
            config_string: {
                ...prevConfig.config_string,
                user_config: {
                    ...prevConfig.config_string.user_config,
                    [field]: value,
                },
            },
        }));
    };

    const handleObservedTickersChange = (updatedTickers) => {
        updateConfigField('tickers', updatedTickers.map((ticker) => ticker.symbol.replace(/^\$/, '')));
    };

    const handleSaveConfig = async () => {
        try {
            const response = await fetch(`http://localhost:8000/api/config/${config.config_id}/`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    config_string: config.config_string,
                }),
            });
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            setModalMessage('Konfiguracja została pomyślnie zapisana!');
            setIsModalOpen(true);
            fetchConfig();
        } catch (err) {
            setModalMessage(`Wystąpił błąd: ${err.message}`);
            setIsModalOpen(true);
        }
    };

    const Modal = ({ isOpen, message, onClose }) => {
        if (!isOpen) return null;
        return (
            <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
                <div className="bg-white p-6 rounded-lg shadow-lg max-w-md w-full relative">
                    <button
                        className="absolute top-2 right-2 text-gray-500 hover:text-gray-800"
                        onClick={onClose}
                    >
                        ✕
                    </button>
                    <h2 className="text-xl font-semibold mb-4">Informacja</h2>
                    <p className="text-gray-700">{message}</p>
                    <div className="mt-6 text-right">
                        <button
                            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                            onClick={onClose}
                        >
                            OK
                        </button>
                    </div>
                </div>
            </div>
        );
    };

    return (
        <main className="relative p-8 bg-gray-900 min-h-screen text-gray-200">
            <h1 className="text-3xl font-bold mb-6">Config Page</h1>

            {loading ? (
                <p>Loading configuration...</p>
            ) : error ? (
                <p className="text-red-400">{error}</p>
            ) : !config ? (
                <p>No active configuration found.</p>
            ) : (
                <>
                    <div className="mb-4">
                        <label className="inline-flex items-center cursor-pointer">
                            <input
                                type="checkbox"
                                checked={isJsonEditorMode}
                                onChange={() => setIsJsonEditorMode(!isJsonEditorMode)}
                                className="form-checkbox h-5 w-5 text-blue-500"
                            />
                            <span className="ml-2 text-sm">Edit as JSON</span>
                        </label>
                    </div>

                    {isJsonEditorMode ? (
                        <JsonEditor
                            initialConfig={config}
                            onCancel={() => setIsJsonEditorMode(false)}
                            onSave={handleSaveConfig}
                        />
                    ) : (
                        <>
                            <div className="mb-6 p-4">
                                <h2 className="text-2xl font-semibold">{config.name}</h2>
                                <p className="text-sm text-gray-400">
                                    Last modified: {formatDate(config.uptaded_at)}
                                </p>
                            </div>

                            <div className="mb-6 p-4 bg-gray-800 rounded-lg shadow-lg">
                                <h3 className="text-lg font-semibold mb-4">User Configuration</h3>
                                <div className="px-4">
                                    <label className="block text-sm font-medium text-gray-300">Select Model</label>
                                    <select
                                        value={config.config_string.user_config.model}
                                        onChange={(e) => updateConfigField('model', e.target.value)}
                                        className="mt-1 block w-full px-4 py-2 bg-gray-800 border border-gray-600 rounded-md text-gray-200 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                    >
                                        <option value="LSTMCNNv1">LSTMCNNv1</option>
                                    </select>
                                </div>

                                <div className="mt-4">
                                    <TickersTile
                                        availableTickers={availableTickers}
                                        observedTickersProp={config.config_string.user_config.tickers.map(
                                            (ticker) => ({ symbol: `$${ticker}`, full_name: ticker })
                                        )}
                                        onObservedTickersChange={handleObservedTickersChange}
                                    />
                                </div>
                            </div>

                            <div className="mb-6 p-4 bg-gray-800 rounded-lg shadow-lg">
                                <h3 className="text-lg font-semibold mb-4">Scraper Configuration</h3>
                                <ConfigTile />
                            </div>
                        </>
                    )}
                </>
            )}

            <button
                onClick={handleSaveConfig}
                className="sticky bottom-8 right-[-1] bg-gray-500 text-white p-4 px-5 transition rounded-full shadow-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                title="Zapisz config"
            >
                <FontAwesomeIcon icon={faSave} />
            </button>

            <Modal isOpen={isModalOpen} message={modalMessage} onClose={() => setIsModalOpen(false)} />
        </main>
    );
}
