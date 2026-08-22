'use client';
import React, { useEffect, useState } from 'react';
import Tile from '../common/Tile';
import apiFetch from '../../utils/apiFetch';

const POLL_INTERVAL_MS = 15000;
const MAX_TWEETS_SHOWN = 6;

const SENTIMENT_LABELS = { 0: 'Negative', 1: 'Neutral', 2: 'Positive' };
const SENTIMENT_COLORS = { 0: 'text-red-400', 1: 'text-yellow-400', 2: 'text-green-400' };

export default function LiveTweetsFeedTile() {
    const [tweets, setTweets] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchTweets = async () => {
        try {
            const response = await apiFetch('/api/posts/?ordering=-time_stamp&page=1');
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const data = await response.json();
            const results = Array.isArray(data) ? data : data?.results ?? [];
            setTweets(results.slice(0, MAX_TWEETS_SHOWN));
            setError(null);
        } catch (err) {
            setError(`Error fetching tweets: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTweets();
        const id = setInterval(fetchTweets, POLL_INTERVAL_MS);
        return () => clearInterval(id);
    }, []);

    return (
        <Tile>
            <h2 className="text-sm font-semibold mb-2 text-gray-200">Live Feed — Tweets</h2>

            {loading ? (
                <p className="text-gray-400 text-xs">Loading tweets...</p>
            ) : error ? (
                <p className="text-red-400 text-xs">{error}</p>
            ) : tweets.length > 0 ? (
                <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {tweets.map((post) => (
                        <div key={post.post_id} className="bg-gray-700 rounded-md p-1.5 text-xs">
                            <div className="flex justify-between items-center text-[11px] text-gray-400 mb-0.5">
                                <div className="flex items-center gap-1.5">
                                    <span className="font-semibold text-blue-400">
                                        {post.related_ticker?.symbol}
                                    </span>
                                    {post.post_prediction && (
                                        <span
                                            className={`font-semibold ${
                                                SENTIMENT_COLORS[post.post_prediction.prediction] ?? 'text-gray-400'
                                            }`}
                                        >
                                            {SENTIMENT_LABELS[post.post_prediction.prediction] ?? 'Unknown'}
                                        </span>
                                    )}
                                    {post.post_prediction?.probabilities && (
                                        <span className="text-gray-500">
                                            [{post.post_prediction.probabilities.map((p) => p.toFixed(2)).join(', ')}]
                                        </span>
                                    )}
                                </div>
                                <span>{new Date(post.time_stamp).toLocaleString()}</span>
                            </div>
                            <p className="text-gray-200">{post.related_content?.text}</p>
                        </div>
                    ))}
                </div>
            ) : (
                <p className="text-gray-400 text-xs">No tweets available yet.</p>
            )}
        </Tile>
    );
}
