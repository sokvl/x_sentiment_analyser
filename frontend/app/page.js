'use client'

import SignalForecastTile from './components/signals/SignalForecastTile';
import ScraperStatusTile from './components/scraper/ScraperStatusTile';
import TickerDataTile from './components/tickers/TickerDataTile';
import { useUserConfig } from './utils/UserConfigContext';

export default function Home() {
    const { state: userConfig } = useUserConfig(); // Get user configuration

    return (
        <main className="p-8 bg-gray-900 min-h-screen">
        <div className="flex flex-col lg:flex-row gap-6">
            <div className="flex-1">
                <SignalForecastTile tickers={userConfig.tickers} />
                <TickerDataTile styles={'my-2'}/>
            </div>
        <div className="flex-1 max-w-sm">
            <ScraperStatusTile
                status="RUNNING"
                website="x.com"
                ticker="$TSLA"
                tweetCount={123}
                buttonsVisible={false}
            />
        </div>
    </div>
</main>

    );
}
