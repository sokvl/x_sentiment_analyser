import React from 'react';
import Tile from '../common/Tile';


export default function ResultsTableTile() {
    const correctPredictions = mockResults.filter(
        (row) => row.prediction === row.actual
    ).length;

    const accuracyPercentage = ((correctPredictions / mockResults.length) * 100).toFixed(2);

    return (
        <Tile>
            <h2 className="text-lg font-semibold mb-4 text-gray-200">Prediction Results</h2>

            <div className="overflow-x-auto">
                <table className="w-full text-sm border-collapse">
                    <thead>
                        <tr className="bg-gray-700 text-gray-300">
                            <th className="p-3 text-left">Date</th>
                            <th className="p-3 text-left">Ticker</th>
                            <th className="p-3 text-left">Prediction</th>
                            <th className="p-3 text-left">Actual</th>
                        </tr>
                    </thead>
                    <tbody>
                        {mockResults.map((row, index) => (
                            <tr
                                key={index}
                                className="border-t border-gray-700 hover:bg-gray-800"
                            >
                                <td className="p-3 text-gray-300">{row.date}</td>
                                <td className="p-3 font-semibold text-gray-200">
                                    {row.ticker}
                                </td>
                                <td
                                    className={`p-3 ${
                                        row.prediction === 'BUY'
                                            ? 'text-green-400'
                                            : 'text-red-400'
                                    }`}
                                >
                                    {row.prediction}
                                </td>
                                <td
                                    className={`p-3 ${
                                        row.actual === 'BUY'
                                            ? 'text-green-400'
                                            : 'text-red-400'
                                    }`}
                                >
                                    {row.actual}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Podsumowanie */}
            <p className="mt-4 text-gray-200">
                % Correct for <strong>AAPL</strong>: {accuracyPercentage}%
            </p>
        </Tile>
    );
}
