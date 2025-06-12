'use client'

import React from 'react';
import CsvUploadTile from '../components/benchmark/CsvUploadTile';
import ChartTile from '../components/benchmark/SentimentAndCandlestickChartTile';
import ResultsTableTile from '../components/benchmark/ResultsTableTile';
import SentimentAndCandlestickChartTile from '../components/benchmark/SentimentAndCandlestickChartTile';
import Tile from '../components/common/Tile';
import PredictionReportTile from '../components/benchmark/PredictionReportTile';


export default function Benchmark() {
    return (
        <main className="p-8 bg-gray-900 min-h-screen">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <CsvUploadTile />
                <PredictionReportTile />
            </div>
        </main>
    );
}
