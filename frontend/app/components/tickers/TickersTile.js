'use client';
import React, { useState, useEffect } from 'react';
import Tile from '../common/Tile';

export default function TickersTile({
  configId=4,
  availableTickers = [],
  observedTickersProp = [],
  onObservedTickersChange,
}) {
  const [observedTickers, setObservedTickers] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredTickers, setFilteredTickers] = useState(availableTickers);

  useEffect(() => {
    if (observedTickersProp.length > 0) {
      setObservedTickers(observedTickersProp);
    }
  }, [observedTickersProp]);

  const patchTickersToBackend = async (updatedTickers) => {
    try {
      const patchBody = {
        config_string: {
          user_config: {

            tickers: updatedTickers.map((t) => t.symbol),
          },
        },
      };

      const response = await fetch(`http://localhost:8000/api/config/${configId}/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patchBody),
      });
      if (!response.ok) {
        throw new Error('Patch request failed');
      }
      const data = await response.json();
      console.log('Patch request succeeded:', data);
    } catch (error) {
      console.error('Error while patching tickers:', error);
    }
  };

  // Aktualizacja obserwowanych tickerów → dodanie
  const addObservedTicker = (ticker) => {
    if (!observedTickers.find((t) => t.symbol === ticker.symbol)) {
      const updatedTickers = [...observedTickers, ticker];
      setObservedTickers(updatedTickers);
      onObservedTickersChange(updatedTickers);
      // Możesz też automatycznie patchować do backendu już przy dodawaniu
      patchTickersToBackend(updatedTickers);
    }
  };

  // Aktualizacja obserwowanych tickerów → usunięcie
  const removeObservedTicker = (ticker) => {
    const updatedTickers = observedTickers.filter((t) => t.symbol !== ticker.symbol);
    setObservedTickers(updatedTickers);
    onObservedTickersChange(updatedTickers);
    // PATCH do backendu, żeby od razu odzwierciedlić zmianę
    patchTickersToBackend(updatedTickers);
  };

  // Funkcja obsługi wyszukiwania
  const handleSearch = (query) => {
    setSearchQuery(query);
    const unobservedTickers = availableTickers.filter(
      (ticker) => !observedTickers.some((observed) => observed.symbol === ticker.symbol)
    );
    setFilteredTickers(
      unobservedTickers.filter((ticker) =>
        ticker.symbol.toLowerCase().includes(query.toLowerCase())
      )
    );
  };

  // Reset listy filtrowanej przy aktualizacji `availableTickers` albo `observedTickers`
  useEffect(() => {
    const unobservedTickers = availableTickers.filter(
      (ticker) => !observedTickers.some((observed) => observed.symbol === ticker.symbol)
    );
    setFilteredTickers(unobservedTickers);
  }, [availableTickers, observedTickers]);

  return (
    <Tile>
      <h2 className="text-lg font-semibold mb-4 text-gray-200">
        Observed Tickers
      </h2>

      {/* Sekcja Observed Tickers */}
      <div className="mb-4">
        <div className="flex flex-wrap gap-2 mt-2">
          {observedTickers.map((ticker) => (
            <div
              key={ticker.symbol}
              className="flex items-center bg-gray-700 px-3 py-1 rounded-lg text-sm text-gray-200"
            >
              {ticker.symbol}
              <button
                onClick={() => removeObservedTicker(ticker)}
                className="ml-2 text-red-400 hover:text-red-600"
              >
                &times;
              </button>
            </div>
          ))}
          {observedTickers.length === 0 && (
            <p className="text-gray-400 text-sm">No observed tickers</p>
          )}
        </div>
      </div>

      {/* Wyszukiwanie */}
      <input
        type="text"
        placeholder="Select from supported tickers..."
        value={searchQuery}
        onChange={(e) => handleSearch(e.target.value)}
        className="w-full px-4 py-2 mb-4 rounded-md bg-gray-800 text-gray-200 border border-gray-600 focus:outline-none focus:border-blue-500"
      />

      {/* Lista "nieobserwowanych" tickerów do wyboru */}
      <div className="max-h-60 overflow-auto border border-gray-700 rounded-md">
        {filteredTickers.length > 0 ? (
          filteredTickers.map((ticker) => (
            <div
              key={ticker.symbol}
              onClick={() => addObservedTicker(ticker)}
              className="px-4 py-2 hover:bg-gray-700 text-gray-300 cursor-pointer"
            >
              {ticker.symbol} - {ticker.full_name}
            </div>
          ))
        ) : (
          <p className="text-gray-400 text-center p-2">
            No available tickers
          </p>
        )}
      </div>
    </Tile>
  );
}
