'use client';
import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import Tile from '../common/Tile';
import ModalWithTimer from '../common/ModalWithTimer';

import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPause, faArrowsRotate, faForward, faSquare } from '@fortawesome/free-solid-svg-icons';

const STATUS_COLORS = {
    IDLE: 'bg-gray-500',
    CONFIG: 'bg-blue-500',
    RUNNING: 'bg-green-500',
    PAUSED: 'bg-yellow-500',
    STOPPED: 'bg-red-500',
};

export default function ScraperStatusTile({ status, website, ticker, tweetCount, showStartButton, buttonsVisible=true }) {
    const [logs, setLogs] = useState([]);
    const [task, setTask] = useState({});
    const [loading, setLoading] = useState(false);
    const [scraperState, setScraperState] = useState('IDLE');
    const [error, setError] = useState(null);
    const [modalMessage, setModalMessage] = useState(null); // Wiadomość dla modala

    const fetchLogs = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/scraper/logs/?source=twitter');
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const data = await response.json();
            setScraperState(data.state || 'IDLE');
            setLogs(data.logs || []);
            setTask(data.current_task || {});
        } catch (err) {
            setError(err.message);
        }
    };

    const handleAction = async (action) => {
        setLoading(true);
        setModalMessage(null);
        try {
            const response = await fetch(`http://localhost:8000/api/scraper/${action.toLowerCase()}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    source: 'twitter',
                }).toString(),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            const data = await response.json();
            console.log(`${action} action successful:`, data);
            setScraperState(data.state || scraperState);

            setModalMessage(`${action} action successful: ${data.message || 'No additional info provided.'}`);
            if (response.status === 200) {
                fetchLogs();
            }
        } catch (err) {
            setModalMessage(`Error performing ${action}: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        const id = setInterval(() => {
            fetchLogs();
        }, 10000);

        return () => clearInterval(id);
    }, []);

    return (
        <Tile className="p-4 bg-gray-800 rounded-lg shadow-lg text-gray-200">
            {/* Modal wyświetlany po akcji */}
            {modalMessage && (
                <ModalWithTimer
                    text={modalMessage}
                    duration={7000} // 4 sekundy
                    onClose={() => setModalMessage(null)}
                />
            )}

            <div className="flex justify-between items-center mb-4">
                <div>
                    <h2 className="text-lg font-semibold">Scraper Status</h2>
                    <p className="text-sm">
                        <strong>Website:</strong> {task?.source || 'None'}
                    </p>
                    <p className="text-sm">
                        <strong>Ticker:</strong> {task?.ticker || 'None'}
                    </p>
                    <p className="text-sm">
                        <strong>Tweet Count:</strong> {task?.count || 'None'}
                    </p>
                </div>
                <div className="flex items-center">
                    <span className="mr-2 text-sm font-medium">STATUS:</span>
                    <div className={`w-4 h-4 rounded-full ${STATUS_COLORS[scraperState] || 'bg-gray-500'}`}></div>
                </div>
            </div>

            <h3 className="text-md font-semibold mb-2">Logs</h3>
            {loading ? (
                <p>Loading logs...</p>
            ) : error ? (
                <p className="text-red-500">Error: {error}</p>
            ) : logs.length > 0 ? (
                <div className="bg-gray-700 rounded-md p-2 h-48 overflow-auto text-sm">
                    {logs.map((log, index) => (
                        <p key={index} className="text-gray-300">
                            {log}
                        </p>
                    ))}
                </div>
            ) : (
                <p className="text-gray-400">No logs available.</p>
            )}

            {/* Przycisk akcji w zależności od stanu scrapera */}
            { buttonsVisible ? (
            <div className="mt-4 flex justify-center gap-4">
                {scraperState === 'IDLE' || scraperState === 'STOPPED' ? (
                    showStartButton && (
                        <button
                            onClick={() => handleAction('START')}
                            disabled={loading}
                            className={`px-4 py-2 rounded bg-blue-600 text-white ${
                                loading ? 'opacity-50 cursor-not-allowed' : 'hover:bg-blue-700'
                            }`}
                        >
                            <i className="fas fa-play mr-2"></i>
                            {loading ? 'Starting...' : 'Start Scraper'}
                        </button>
                    )
                ) : (
                    <>
                        <button
                            onClick={() => handleAction('resume')}
                            disabled={scraperState === 'RUNNING' || loading}
                            className="px-4 py-3 rounded bg-gray-700 text-gray-200 hover:bg-gray-900 shadow-xl"
                        >
                            <FontAwesomeIcon icon={faForward} />
                        </button>
                        <button
                            onClick={() => handleAction('pause')}
                            disabled={scraperState === 'PAUSED' || loading}
                            className="px-4 py-3 rounded bg-gray-700 text-gray-200 hover:bg-gray-900 shadow-xl"
                        >
                            <FontAwesomeIcon icon={faPause} />
                        </button>
                        <button
                            onClick={() => handleAction('restart')}
                            disabled={loading}
                            className="px-4 py-3 rounded bg-gray-700 text-gray-200 hover:bg-gray-900 shadow-xl"
                        >
                            <FontAwesomeIcon icon={faArrowsRotate} />
                        </button>
                        <button
                            onClick={() => handleAction('stop')}
                            disabled={scraperState === 'STOPPED' || loading}
                            className="px-4 py-3 rounded bg-gray-700 text-gray-200 hover:bg-gray-900 shadow-xl"
                        >
                            <FontAwesomeIcon icon={faSquare} />
                        </button>
                    </>
                )}
            </div>
            ) : ( <></>)}
        </Tile>
    );
}

ScraperStatusTile.propTypes = {
    status: PropTypes.oneOf(['IDLE', 'CONFIG', 'RUNNING', 'PAUSED', 'STOPPED']).isRequired,
    website: PropTypes.string.isRequired,
    ticker: PropTypes.string.isRequired,
    tweetCount: PropTypes.number.isRequired,
    showStartButton: PropTypes.bool,
};

ScraperStatusTile.defaultProps = {
    showStartButton: true,
};
