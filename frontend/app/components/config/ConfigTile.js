'use client';
import React, { useEffect, useState } from 'react';

export default function ConfigTile({ initialConfig = {}, onConfigChange }) {
  const [mode, setMode] = useState('crawl');
  const [authRequired, setAuthRequired] = useState(false);
  const [email, setEmail] = useState('');
  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');

  const [source, setSource] = useState('twitter');
  const [crawlInterval, setCrawlInterval] = useState(60);
  const [startDate, setStartDate] = useState(getYesterdayDate());
  const [endDate, setEndDate] = useState(getTodayDate());
  const [filters, setFilters] = useState(['links']);
  const [keywords, setKeywords] = useState('stock, market');
  const [tickers, setTickers] = useState(['TSLA', 'NVDA', 'AAPL', 'MSFT', 'GOOG']);

  // -- Helpery do dat
  function getYesterdayDate() {
    const date = new Date();
    date.setDate(date.getDate() - 1);
    return date.toISOString().split('T')[0];
  }
  function getTodayDate() {
    return new Date().toISOString().split('T')[0];
  }


  useEffect(() => {
    const finalConfig = {
      config_id: initialConfig.config_id || 4,
      name: initialConfig.name || 'Test Config',
      active: initialConfig.active !== undefined ? initialConfig.active : true,
      created_at: initialConfig.created_at || new Date().toISOString(),
      updated_at: new Date().toISOString(),
      config_string: {
        user_config: {
          model: initialConfig.config_string?.user_config?.model || 'LSTMCNNv1',
          tickers: tickers, // z naszego stanu
        },
        scrapers_config: [
          {
            source: [
              {
                name: source,
                base_url: 'https://x.com/search?q=',
              },
            ],
            threads: 1,
            credentials: authRequired
              ? {
                  email,
                  login,
                  password,
                }
              : {},
            twitter_query: {
              params: {
                lang: 'en',
                filter: filters,
                keywords: keywords
                  .split(',')
                  .map((k) => k.trim())
                  .filter(Boolean),
              },
              start_date: startDate,
              end_date: endDate,
            },
            crawl_interval: Number(crawlInterval),
            max_time_running: null,
            mode,
          },
        ],
      },
    };
    if (typeof onConfigChange === 'function') {
      onConfigChange(finalConfig);
    }
  }, [
    mode,
    authRequired,
    email,
    login,
    password,
    source,
    crawlInterval,
    startDate,
    endDate,
    filters,
    keywords,
    tickers,
    initialConfig,
    onConfigChange,
  ]);

  return (
    <div className="p-6 bg-gray-900 text-gray-200 rounded-lg shadow-lg max-w-3xl mx-auto">
      <div className="flex items-center gap-4 mb-4">
        <label className="flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={mode === 'crawl'}
            onChange={() => {
              const newMode = mode === 'crawl' ? 'scrape' : 'crawl';
              setMode(newMode);
              if (newMode === 'crawl') {
                setStartDate(getYesterdayDate());
                setEndDate(getTodayDate());
              }
            }}
            className="form-checkbox h-5 w-5 text-blue-500"
          />
          <span className="ml-2">Crawl Mode</span>
        </label>
      </div>

      {/* Crawl Interval */}
      <label className="block mb-4">
        {mode === 'crawl'
          ? 'Crawl Interval (seconds):'
          : 'Scraping (możesz użyć tego samego pola - nazwa do zmiany):'}
        <input
          type="number"
          placeholder={mode === 'scrape' ? 'Scraping placeholder' : '60'}
          value={crawlInterval}
          onChange={(e) => setCrawlInterval(e.target.value)}
          className="w-full p-2 mt-1 rounded-md bg-gray-800 border border-gray-700"
        />
      </label>

      {/* Source */}
      <label className="block mb-4">
        Source:
        <div className="flex gap-4 mt-1">
          <select
            value={source}
            onChange={(e) => setSource(e.target.value)}
            className="w-full p-2 py-1 rounded-md bg-gray-800 border border-gray-700"
          >
            <option value="twitter">twitter (x.com)</option>            {/* Możesz dodać inne źródła */}
          </select>
        </div>
      </label>

      {/* Auth Required */}
      <label className="flex items-center cursor-pointer mb-4">
        <input
          type="checkbox"
          checked={authRequired}
          onChange={() => setAuthRequired((prev) => !prev)}
          className="form-checkbox h-5 w-5 text-blue-500"
        />
        <span className="ml-2">Auth Required</span>
      </label>

      {/* Formularz na credentiale tylko, gdy authRequired = true */}
      {authRequired && (
        <div className="grid grid-cols-2 gap-4 mb-4">
          <input
            type="email"
            placeholder="Email"
            className="w-full p-2 rounded-md bg-gray-800 border border-gray-700"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            type="text"
            placeholder="Username"
            className="w-full p-2 rounded-md bg-gray-800 border border-gray-700"
            value={login}
            onChange={(e) => setLogin(e.target.value)}
          />
          <input
            type="password"
            placeholder="Password"
            className="col-span-2 w-full p-2 rounded-md bg-gray-800 border border-gray-700"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
      )}

      {/* Query Configuration */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold mb-2">Query</h3>

        {/* Filters */}
        <div>
          <span className="block mb-1">Filters:</span>
          {['links', 'replies', 'media'].map((filter) => (
            <label key={filter} className="flex items-center gap-2 mb-1">
              <input
                type="checkbox"
                checked={filters.includes(filter)}
                onChange={() => {
                  setFilters((prev) => {
                    if (prev.includes(filter)) {
                      return prev.filter((f) => f !== filter);
                    } else {
                      return [...prev, filter];
                    }
                  });
                }}
                className="form-checkbox h-4 w-4 text-blue-500"
              />
              <span>{filter}</span>
            </label>
          ))}
        </div>

        {/* Language (zafiksowane "en") */}
        <label>
          Language:
          <input
            type="text"
            value="en"
            className="w-full p-2 mt-1 rounded-md bg-gray-800 border border-gray-700"
            readOnly
          />
        </label>

        {/* Keywords */}
        <label>
          Keywords:
          <input
            type="text"
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            placeholder="stock, market, investing..."
            className="w-full p-2 mt-1 rounded-md bg-gray-800 border border-gray-700"
          />
        </label>

        {/* Dates */}
        <div className="flex gap-4">
          <label className="flex-1">
            Start date:
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full p-2 mt-1 rounded-md bg-gray-800 border border-gray-700"
            />
          </label>
          <label className="flex-1">
            End date:
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full p-2 mt-1 rounded-md bg-gray-800 border border-gray-700"
            />
          </label>
        </div>

        {/* Tickers (pod user_config) */}
        <label>
          Tickers (po przecinku):
          <input
            type="text"
            value={tickers.join(', ')}
            onChange={(e) => {
              // Zamień stringa na tablicę
              const newTickers = e.target.value
                .split(',')
                .map((t) => t.trim())
                .filter(Boolean);
              setTickers(newTickers);
            }}
            className="w-full p-2 mt-1 rounded-md bg-gray-800 border border-gray-700"
          />
        </label>
      </div>
    </div>
  );
}
