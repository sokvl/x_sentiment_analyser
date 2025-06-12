import React, { useEffect, useRef } from 'react';
import { createChart, CrosshairMode, LineStyle } from 'lightweight-charts';

export default function SentimentAndCandlestickChartTile({ chartData }) {
    const chartContainerRef = useRef(null);
    const tooltipRef = useRef(null);

    useEffect(() => {
        if (!chartData) return;

        const filteredChartData = Object.fromEntries(
            Object.entries(chartData).filter(([date, data]) => {
                const stock = data.stock_data;
                return (
                    stock &&
                    stock.Open != null &&
                    stock.Close != null &&
                    stock.maxDay != null &&
                    stock.minDay != null
                );
            })
        );

        const chart = createChart(chartContainerRef.current, {
            width: chartContainerRef.current.offsetWidth,
            height: 400,
            layout:
                { textColor: 'white', background: { type: 'solid', color: 'rgba(17, 24, 39, 1)' } },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.1)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.1)' },
            },
            crosshair: {
                mode: CrosshairMode.Normal,
                vertLine: {
                    color: '#758696',
                    width: 1,
                    style: LineStyle.Solid,
                    labelBackgroundColor: '#1e293f',
                },
                horzLine: {
                    color: '#758696',
                    width: 1,
                    style: LineStyle.Solid,
                    labelBackgroundColor: '#1e293f',
                },
            },
            timeScale: {
                borderColor: 'rgba(255, 255, 255, 0.2)',
                timeVisible: true,
                secondsVisible: false,
            },
            rightPriceScale: {
                scaleMargins: {
                    top: 0.1,
                    bottom: 0.1,
                },
            },
        });

        // 2. Candlestick Series
        const candleSeries = chart.addCandlestickSeries({
            upColor: '#22c55e', // Green
            downColor: '#ef4444', // Red
            borderVisible: true,
            wickUpColor: '#22c55e',
            wickDownColor: '#ef4444',
        });

        const candles = Object.entries(filteredChartData)
            .map(([date, data]) => ({
                time: new Date(date).getTime() / 1000,
                open: data.stock_data.Open,
                high: data.stock_data.maxDay,
                low: data.stock_data.minDay,
                close: data.stock_data.Close,
            }))
            .sort((a, b) => a.time - b.time);

        candleSeries.setData(candles);

        // 3. Sentiment Line Series
        const sentimentSeries = chart.addLineSeries({
            color: 'rgb(194, 194, 194)', // Bright Orange for better visibility
            lineWidth: 2, // Increased line width
            crosshairMarkerVisible: true,
            priceScaleId: 'sentiment',
            lastValueVisible: true,
            lineStyle: LineStyle.Solid,
        });

        const sentiments = Object.entries(filteredChartData)
            .map(([date, data]) => ({
                time: new Date(date).getTime() / 1000,
                value: data.sentiment_score,
            }))
            .sort((a, b) => a.time - b.time);

        sentimentSeries.setData(sentiments);

        // 4. Configure Sentiment Price Scale
        chart.priceScale('sentiment').applyOptions({
            position: 'left',
            scaleMargins: {
                top: 0.3,
                bottom: 0.25,
            },
            borderColor: 'rgba(255, 165, 0, 0.8)', // Matching sentiment line color
            visible: true,
        });

        // 5. Add a legend
        const legend = document.createElement('div');
        legend.style.position = 'absolute';
        legend.style.top = '10px';
        legend.style.right = '10px';
        legend.style.background = 'rgba(0, 0, 0, 0.5)';
        legend.style.color = '#fff';
        legend.style.padding = '5px 10px';
        legend.style.borderRadius = '4px';
        legend.style.fontSize = '12px';
        legend.innerHTML = `
            <span style="display: inline-block; width: 12px; height: 12px; background: #22c55e; margin-right: 5px;"></span>Candlestick
            <span style="display: inline-block; width: 12px; height: 12px; background: rgb(255, 165, 0); margin: 0 5px 0 15px;"></span>Sentiment
        `;
        chartContainerRef.current.appendChild(legend);

        // 6. Custom Tooltip
        const tooltip = document.createElement('div');
        tooltip.style.position = 'absolute';
        tooltip.style.display = 'none';
        tooltip.style.pointerEvents = 'none';
        tooltip.style.background = 'rgba(0, 0, 0, 0.8)';
        tooltip.style.color = '#fff';
        tooltip.style.padding = '8px';
        tooltip.style.borderRadius = '4px';
        tooltip.style.fontSize = '12px';
        tooltip.style.zIndex = '1000';
        tooltipRef.current = tooltip;
        chartContainerRef.current.appendChild(tooltip);

        const handleMouseMove = (param) => {
            if (!param.time || !param.point) {
                tooltip.style.display = 'none';
                return;
            }

            const time = param.time;

            // Retrieve candle data for the hovered time
            const candle = candleSeries.data().find((d) => d.time === time);
            const sentiment = sentimentSeries.data().find((d) => d.time === time);

            if (!candle || sentiment === undefined) {
                tooltip.style.display = 'none';
                return;
            }

            // Position the tooltip based on the mouse position
            const x = param.point.x;
            const y = param.point.y;

            tooltip.innerHTML = `
                <div><strong>Date:</strong> ${new Date(time * 1000).toLocaleDateString()}</div>
                <div><strong>Open:</strong> ${candle.open}</div>
                <div><strong>High:</strong> ${candle.high}</div>
                <div><strong>Low:</strong> ${candle.low}</div>
                <div><strong>Close:</strong> ${candle.close}</div>
                <div><strong>Sentiment:</strong> ${sentiment.value}</div>
            `;
            tooltip.style.left = `${x + 15}px`;
            tooltip.style.top = `${y + 15}px`;
            tooltip.style.display = 'block';
        };

        const handleMouseLeave = () => {
            if (tooltipRef.current) {
                tooltipRef.current.style.display = 'none';
            }
        };

        // Subscribe to crosshair move events
        chart.subscribeCrosshairMove(handleMouseMove);

        // Add a DOM event listener for mouse leave
        const chartContainer = chartContainerRef.current;
        if (chartContainer) {
            chartContainer.addEventListener('mouseleave', handleMouseLeave);
        }

        // Handle responsiveness
        const handleResize = () => {
            if (chartContainerRef.current) {
                chart.applyOptions({ width: chartContainerRef.current.offsetWidth });
                chart.timeScale().fitContent();
            }
        };

        window.addEventListener('resize', handleResize);

        // Initial resize to set chart width
        handleResize();

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.unsubscribeCrosshairMove(handleMouseMove);
            if (chartContainer) {
                chartContainer.removeEventListener('mouseleave', handleMouseLeave);
            }
            chart.remove();
        };
    }, [chartData]);

    return (
        <div className="p-4 bg-gray-800 rounded-lg shadow-lg relative">
            <h2 className="text-lg font-semibold mb-4 text-gray-200">Stock Prices & Sentiment</h2>
            <div ref={chartContainerRef} style={{ height: '400px', width: '100%', position: 'relative' }} />
        </div>
    );
}
