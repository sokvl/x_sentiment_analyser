import {
    //Chart as ChartJS,
    LinearScale,
    TimeScale,
    Tooltip,
    Legend,
    PointElement,
    LineElement,
} from 'chart.js';
import { CandlestickController, CandlestickElement } from 'chartjs-chart-financial';
import 'chartjs-adapter-date-fns'; // Adapter dat
import Chart from 'chart.js/auto';
// Rejestracja wymaganych elementów
export function registerChartElements() {
    Chart.register(
        LinearScale,
        TimeScale,
        Tooltip,
        Legend,
        CandlestickController,
        CandlestickElement,
        PointElement,
        LineElement
    );
}

// Funkcja pomocnicza do generowania losowych danych
export function generateRandomCandlestickData(count, startDate) {
    const data = [];
    const sentimentData = [];
    let currentDate = new Date(startDate);
    let lastClose = 100;

    for (let i = 0; i < count; i++) {
        currentDate.setDate(currentDate.getDate() + 1);

        const open = parseFloat((lastClose * (0.98 + Math.random() * 0.07)).toFixed(2));
        const close = parseFloat((open * (0.98 + Math.random() * 0.07)).toFixed(2));
        const high = parseFloat((Math.max(open, close) * (1.01 + Math.random() * 0.02)).toFixed(2));
        const low = parseFloat((Math.min(open, close) * (0.99 - Math.random() * 0.02)).toFixed(2));
        const sentiment = parseFloat((-1 + Math.random() * 2).toFixed(2));

        data.push({
            x: new Date(currentDate),
            o: open,
            h: high,
            l: low,
            c: close,
        });

        sentimentData.push({
            x: new Date(currentDate),
            y: sentiment,
        });

        lastClose = close;
    }

    return { candleData: data, sentimentData };
}
