'use client';
import React, { useEffect, useState } from 'react';
import Tile from '../common/Tile';
import apiFetch from '../../utils/apiFetch';
import SentimentTag from './SentimentTag';

const POLL_INTERVAL_MS = 15000;
const MAX_NEWS_SHOWN = 6;

export default function LiveNewsFeedTile() {
    const [news, setNews] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchNews = async () => {
        try {
            const response = await apiFetch('/api/news/finnhub/');
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const data = await response.json();
            const results = Array.isArray(data) ? data : [];
            setNews(results.slice(0, MAX_NEWS_SHOWN));
            setError(null);
        } catch (err) {
            setError(`Error fetching news: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchNews();
        const id = setInterval(fetchNews, POLL_INTERVAL_MS);
        return () => clearInterval(id);
    }, []);

    return (
        <Tile>
            <h2 className="text-sm font-semibold mb-2 text-gray-200">Live Feed — News</h2>

            {loading ? (
                <p className="text-gray-400 text-xs">Loading news...</p>
            ) : error ? (
                <p className="text-red-400 text-xs">{error}</p>
            ) : news.length > 0 ? (
                <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {news.map((item, index) => (
                        <div key={item.url || index} className="bg-gray-700 rounded-md p-1.5 text-xs">
                            <div className="flex justify-between items-center text-[11px] text-gray-400 mb-0.5">
                                <div className="flex items-center gap-1.5">
                                    <span className="font-semibold text-blue-400">{item.ticker}</span>
                                    <SentimentTag prediction={item.prediction} probabilities={item.probabilities} />
                                    {item.publisher && (
                                        <span className="text-gray-500">{item.publisher}</span>
                                    )}
                                </div>
                                <span>{item.published_at ? new Date(item.published_at).toLocaleString() : ''}</span>
                            </div>
                            {item.url ? (
                                <a
                                    href={item.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-gray-200 hover:text-blue-300 hover:underline"
                                >
                                    {item.headline}
                                </a>
                            ) : (
                                <p className="text-gray-200">{item.headline}</p>
                            )}
                        </div>
                    ))}
                </div>
            ) : (
                <p className="text-gray-400 text-xs">No news available yet.</p>
            )}
        </Tile>
    );
}
