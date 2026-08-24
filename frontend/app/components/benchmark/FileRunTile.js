'use client';
import React, { useEffect, useState } from 'react';
import Tile from '../common/Tile';
import SentimentAndCandlestickChartTile from './SentimentAndCandlestickChartTile';
import apiFetch from '../../utils/apiFetch';

export default function FileRunTile() {
    const [files, setFiles] = useState([]);
    const [selectedFileId, setSelectedFileId] = useState('');
    const [loadingFiles, setLoadingFiles] = useState(true);
    const [filesError, setFilesError] = useState(null);

    const [running, setRunning] = useState(false);
    const [runError, setRunError] = useState(null);
    const [results, setResults] = useState({});
    const [errors, setErrors] = useState([]);
    const [activeTicker, setActiveTicker] = useState(null);

    useEffect(() => {
        const fetchFiles = async () => {
            try {
                const response = await apiFetch('/api/signals/files/');
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                const data = await response.json();
                const results = Array.isArray(data) ? data : data?.results ?? [];
                setFiles(results);
                if (results.length > 0) {
                    setSelectedFileId(String(results[0].file_id));
                }
            } catch (err) {
                setFilesError(`Error fetching files: ${err.message}`);
            } finally {
                setLoadingFiles(false);
            }
        };

        fetchFiles();
    }, []);

    const handleRun = async () => {
        if (!selectedFileId) return;

        setRunning(true);
        setRunError(null);
        setResults({});
        setErrors([]);
        setActiveTicker(null);

        try {
            const response = await apiFetch(`/api/signals/files/${selectedFileId}/run/`);
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || `HTTP error! Status: ${response.status}`);
            }

            setResults(data.results || {});
            setErrors(data.errors || []);
            const tickers = Object.keys(data.results || {});
            if (tickers.length > 0) {
                setActiveTicker(tickers[0]);
            }
        } catch (err) {
            setRunError(`Error running file: ${err.message}`);
        } finally {
            setRunning(false);
        }
    };

    return (
        <Tile>
            <h2 className="text-lg font-semibold mb-4 text-gray-200">Run an Existing File</h2>

            {loadingFiles ? (
                <p className="text-gray-400 text-sm">Loading files...</p>
            ) : filesError ? (
                <p className="text-red-400 text-sm">{filesError}</p>
            ) : files.length === 0 ? (
                <p className="text-gray-400 text-sm">No files available to run.</p>
            ) : (
                <div className="flex flex-col gap-3 mb-4">
                    <select
                        value={selectedFileId}
                        onChange={(e) => setSelectedFileId(e.target.value)}
                        className="w-full p-2 rounded-md bg-gray-800 border border-gray-700 text-gray-200"
                    >
                        {files.map((file) => (
                            <option key={file.file_id} value={file.file_id}>
                                {file.display_name} ({file.row_count ?? '?'} rows)
                            </option>
                        ))}
                    </select>

                    <button
                        onClick={handleRun}
                        disabled={running}
                        className={`flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-blue-600 text-white ${
                            running ? 'opacity-50 cursor-not-allowed' : 'hover:bg-blue-700'
                        }`}
                    >
                        {running && (
                            <span className="h-4 w-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                        )}
                        {running ? 'Running...' : 'Run'}
                    </button>
                </div>
            )}

            {runError && <p className="text-red-400 text-sm mb-4">{runError}</p>}

            {Object.keys(results).length > 0 && (
                <div className="flex space-x-4 mb-6 border-b border-gray-700 overflow-x-auto">
                    {Object.keys(results).map((ticker) => (
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

            {activeTicker && results[activeTicker] && (
                <SentimentAndCandlestickChartTile chartData={results[activeTicker]} ticker={activeTicker} />
            )}

            {errors.length > 0 && (
                <div className="mt-4 p-3 bg-red-700 rounded-md text-sm text-red-100">
                    <h3 className="font-semibold">Errors</h3>
                    {errors.map((error, index) => (
                        <p key={index} className="mt-2">
                            {typeof error === 'string' ? error : JSON.stringify(error)}
                        </p>
                    ))}
                </div>
            )}
        </Tile>
    );
}
