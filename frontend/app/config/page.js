'use client';
import React, { useState, useEffect } from 'react';
import ConfigTile from '../components/config/ConfigTile';
import JsonEditor from '../components/config/JsonEditor';
import JsonToggle from '../components/config/JsonToggle';
import { AVAILABLE_MODELS, DEFAULT_CONFIG } from './constants';
import { useUserConfig } from '../utils/UserConfigContext';

export default function ConfigPage() {
    const { refreshConfig } = useUserConfig();
    const [fullConfig, setFullConfig] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [alert, setAlert] = useState(null);
    const [showJsonEditor, setShowJsonEditor] = useState(false);

    const fetchConfig = async () => {
        setLoading(true);
        try {
            const response = await fetch('http://localhost:8000/api/config/?active=true');
            if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
            const data = await response.json();
            if (data.length > 0) {
                setFullConfig(data[0]);
            } else {
                setFullConfig(DEFAULT_CONFIG);
            }
        } catch (err) {
            setAlert({ type: 'error', message: `Error loading config: ${err.message}` });
            setFullConfig(DEFAULT_CONFIG);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchConfig();
    }, []);

    const handleScraperConfigChange = (updatedScraper) => {
        setFullConfig((prev) => ({
            ...prev,
            config_string: {
                ...prev.config_string,
                scrapers_config: [updatedScraper],
            },
        }));
    };

    const handleUserConfigChange = (field, value) => {
        setFullConfig((prev) => ({
            ...prev,
            config_string: {
                ...prev.config_string,
                user_config: {
                    ...prev.config_string?.user_config,
                    [field]: value,
                },
            },
        }));
    };

    const handleJsonSave = (updatedConfigString) => {
        setFullConfig((prev) => ({ ...prev, config_string: updatedConfigString }));
        setShowJsonEditor(false);
        setAlert({ type: 'success', message: 'JSON applied. Click Save to persist changes.' });
    };

    const handleSave = async () => {
        if (!fullConfig) return;
        setSaving(true);
        setAlert(null);
        try {
            const response = await fetch(
                `http://localhost:8000/api/config/${fullConfig.config_id}/`,
                {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(fullConfig),
                }
            );
            if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
            setAlert({ type: 'success', message: 'Configuration saved successfully!' });
            refreshConfig();
        } catch (err) {
            setAlert({ type: 'error', message: `Error saving config: ${err.message}` });
        } finally {
            setSaving(false);
        }
    };

    const scraperConfig = fullConfig?.config_string?.scrapers_config?.[0] || null;
    const userConfig = fullConfig?.config_string?.user_config || {};

    return (
        <main className="p-8 bg-gray-900 min-h-screen text-gray-200">
            <div className="flex items-center justify-between mb-6">
                <h1 className="text-3xl font-bold">Configuration</h1>
                {fullConfig && (
                    <span className="text-sm text-gray-400">
                        {fullConfig.name}
                        {fullConfig.active && (
                            <span className="ml-2 px-2 py-0.5 text-xs bg-green-800 text-green-200 rounded-full">
                                Active
                            </span>
                        )}
                    </span>
                )}
            </div>

            {alert && (
                <div
                    className={`mb-6 p-4 rounded-md text-sm ${
                        alert.type === 'success'
                            ? 'bg-green-800 text-green-100'
                            : 'bg-red-800 text-red-100'
                    }`}
                >
                    {alert.message}
                </div>
            )}

            {loading ? (
                <div className="text-gray-400 text-center py-16">Loading configuration...</div>
            ) : showJsonEditor ? (
                <JsonEditor
                    initialConfig={fullConfig?.config_string}
                    onSave={handleJsonSave}
                    onCancel={() => setShowJsonEditor(false)}
                />
            ) : (
                <div className="space-y-6">
                    {/* User Config Section */}
                    <div className="p-6 bg-gray-800 rounded-lg shadow-lg">
                        <h2 className="text-xl font-semibold mb-4">User Settings</h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <label className="block">
                                <span className="text-sm text-gray-300">Model</span>
                                <select
                                    value={userConfig.model || 'LSTMCNNv1'}
                                    onChange={(e) => handleUserConfigChange('model', e.target.value)}
                                    className="w-full mt-1 p-2 rounded-md bg-gray-900 border border-gray-700 text-gray-200"
                                >
                                    {AVAILABLE_MODELS.map((m) => (
                                        <option key={m.id} value={m.id}>{m.label}</option>
                                    ))}
                                </select>
                            </label>
                            <label className="block">
                                <span className="text-sm text-gray-300">Tickers (comma separated)</span>
                                <input
                                    type="text"
                                    value={(userConfig.tickers || []).join(', ')}
                                    onChange={(e) => {
                                        const tickers = e.target.value
                                            .split(',')
                                            .map((t) => t.trim().toUpperCase())
                                            .filter(Boolean);
                                        handleUserConfigChange('tickers', tickers);
                                    }}
                                    placeholder="TSLA, NVDA, AAPL..."
                                    className="w-full mt-1 p-2 rounded-md bg-gray-900 border border-gray-700 text-gray-200"
                                />
                            </label>
                        </div>
                    </div>

                    {/* Scraper Config Section */}
                    {scraperConfig && (
                        <div className="bg-gray-800 rounded-lg shadow-lg">
                            <div className="px-6 pt-6">
                                <h2 className="text-xl font-semibold mb-2">Scraper Settings</h2>
                            </div>
                            <ConfigTile
                                config={scraperConfig}
                                onConfigChange={handleScraperConfigChange}
                            />
                        </div>
                    )}

                    {/* JSON Toggle (read-only view) */}
                    <JsonToggle config={fullConfig?.config_string} />

                    {/* Actions */}
                    <div className="flex gap-4">
                        <button
                            onClick={handleSave}
                            disabled={saving}
                            className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-2 rounded-md font-medium"
                        >
                            {saving ? 'Saving...' : 'Save Configuration'}
                        </button>
                        <button
                            onClick={() => setShowJsonEditor(true)}
                            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-md font-medium"
                        >
                            Edit JSON
                        </button>
                    </div>
                </div>
            )}
        </main>
    );
}
