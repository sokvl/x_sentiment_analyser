'use client';
import React, { useState } from 'react';
import Tile from '../common/Tile';

export default function TweetTestTile() {
    const [tweet, setTweet] = useState('');
    const [ticker, setTicker] = useState('');
    const [submitted, setSubmitted] = useState(false);

    const handleSubmit = (e) => {
        e.preventDefault();
        setSubmitted(true);
    };

    return (
        <Tile>
            <h2 className="text-lg font-semibold mb-4 text-gray-200">Test It Yourself</h2>

            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <label htmlFor="tweet" className="block text-sm font-medium text-gray-300">
                        Tweet text
                    </label>
                    <textarea
                        id="tweet"
                        value={tweet}
                        onChange={(e) => {
                            setTweet(e.target.value);
                            setSubmitted(false);
                        }}
                        rows={3}
                        placeholder="Type a tweet to see how the model would read it..."
                        className="mt-1 block w-full px-4 py-2 bg-gray-800 border border-gray-600 rounded-md text-gray-200 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        required
                    />
                </div>

                <div>
                    <label htmlFor="ticker" className="block text-sm font-medium text-gray-300">
                        Ticker
                    </label>
                    <input
                        type="text"
                        id="ticker"
                        value={ticker}
                        onChange={(e) => {
                            setTicker(e.target.value);
                            setSubmitted(false);
                        }}
                        placeholder="$TSLA"
                        className="mt-1 block w-full px-4 py-2 bg-gray-800 border border-gray-600 rounded-md text-gray-200 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        required
                    />
                </div>

                <button
                    type="submit"
                    className="w-full px-4 py-2 rounded-md bg-blue-600 text-white hover:bg-blue-700"
                >
                    Test Sentiment
                </button>
            </form>

            {submitted && (
                <p className="mt-4 text-sm text-yellow-400">
                    🚧 Live sentiment testing is coming soon — this will run your tweet through our model in real time.
                </p>
            )}
        </Tile>
    );
}
