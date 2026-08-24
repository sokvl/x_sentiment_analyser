'use client'

import SignalForecastTile from '../components/signals/SignalForecastTile';
import ScraperStatusTile from '../components/scraper/ScraperStatusTile';
import TickerDataTile from '../components/tickers/TickerDataTile';
import LiveTweetsFeedTile from '../components/dashboard/LiveTweetsFeedTile';
import LiveNewsFeedTile from '../components/dashboard/LiveNewsFeedTile';
import ScraperLiveViewTile from '../components/dashboard/ScraperLiveViewTile';
import SentimentIndexTwitterTile from '../components/dashboard/SentimentIndexTwitterTile';
import SentimentIndexNewsTile from '../components/dashboard/SentimentIndexNewsTile';
import { useUserConfig } from '../utils/UserConfigContext';

export default function Home() {
    const { state: userConfig } = useUserConfig(); // Get user configuration

    return (
        <main className="p-6 bg-gray-900 min-h-screen">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <SignalForecastTile tickers={userConfig.tickers} />
            <TickerDataTile styles="" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex flex-col gap-4">
                <ScraperStatusTile
                    status="RUNNING"
                    website="x.com"
                    ticker="$TSLA"
                    tweetCount={123}
                    buttonsVisible={false}
                />
                <ScraperLiveViewTile />
            </div>
            <div className="flex flex-col gap-4">
                <LiveTweetsFeedTile />
                <LiveNewsFeedTile />
                <div className="grid grid-cols-2 gap-4">
                    <SentimentIndexTwitterTile />
                    <SentimentIndexNewsTile />
                </div>
            </div>
        </div>
        </main>
    );
}
