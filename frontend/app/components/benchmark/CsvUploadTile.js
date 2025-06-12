import React, { useRef, useState } from 'react';
import Tile from '../common/Tile';
import SentimentAndCandlestickChartTile from './SentimentAndCandlestickChartTile';
import ModalWithTimer from '../common/ModalWithTimer';

export default function CsvUploadTile() {
    const fileInputRef = useRef(null);
    const [uploading, setUploading] = useState(false);
    const [results, setResults] = useState({});
    const [errors, setErrors] = useState([]);
    const [message, setMessage] = useState(null);
    const [showModal, setShowModal] = useState(false); // Kontrola widoczności modala
    const [activeTicker, setActiveTicker] = useState(null);

    const handleFileUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        setUploading(true);
        setMessage(null);
        setResults({});
        setErrors([]);
        setActiveTicker(null);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('http://localhost:8000/api/signals/process-csv/', {
                method: 'POST',
                body: formData,
            });
            const data = await response.json()
            console.log(data)
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status} ${data.error}`);
            }

            if (data.results) {
                setResults(data.results);
                setActiveTicker(Object.keys(data.results)[0]);
                setMessage({
                    type: 'success',
                    text: 'File processed successfully. View results below.',
                });
                setShowModal(true);
            }
            if (data.error) {
                setErrors(data.errors);
                setMessage({
                    type: 'error',
                    text: `Errors occurred during processing: ${data.error.length} issues.`,
                });
                setShowModal(true);
            }
        } catch (err) {
            setMessage({
                type: 'error',
                text: `Error: ${err.message}`,
            });
            setShowModal(true);
        } finally {
            setUploading(false);
        }
    };

    return (
        <Tile>
            {/* Modal wyświetlany po przesłaniu */}
            {showModal && message && (
                <ModalWithTimer
                    text={message.text}
                    duration={5000} // 5 sekund
                    onClose={() => setShowModal(false)} // Zamknięcie modala
                />
            )}

            <h2 className="text-lg font-semibold mb-4 text-gray-200">Upload CSV and View Charts</h2>
            <div className="flex flex-col items-center justify-center mb-6">
                <input
                    type="file"
                    accept=".csv"
                    className="hidden"
                    ref={fileInputRef}
                    onChange={handleFileUpload}
                />
                <button
                    onClick={() => fileInputRef.current.click()}
                    disabled={uploading}
                    className={`bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md ${
                        uploading ? 'opacity-50 cursor-not-allowed' : ''
                    }`}
                >
                    {uploading ? 'Uploading...' : 'Select CSV File'}
                </button>
                <p className="text-sm text-gray-400 mt-2">Supported format: *.csv</p>
                <p className="text-sm text-gray-400">File must contain colums: Date, Ticker, Tweet</p>
            </div>

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
                        <div key={index} className="mt-2">
                            <p>
                                <strong>Row:</strong> {error.row}
                            </p>
                            <p>
                                <strong>Details:</strong> {error.details}
                            </p>
                            <p>
                                <strong>Data:</strong> {JSON.stringify(error.data)}
                            </p>
                        </div>
                    ))}
                </div>
            )}
        </Tile>
    );
}
