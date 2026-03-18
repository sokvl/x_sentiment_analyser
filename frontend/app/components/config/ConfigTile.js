'use client';
import React from 'react';
import { AVAILABLE_FILTERS, AVAILABLE_SOURCES } from '../../config/constants';

export default function ConfigTile({ config, onConfigChange }) {
  if (!config) return null;

  // Function to handle updates to the config object
  const handleChange = (fieldOrPath, value) => {
    // Deep copy to avoid mutating state directly
    const newConfig = JSON.parse(JSON.stringify(config));
    
    // Helper to set nested values
    // e.g. handleChange('twitter_query.params.keywords', ['new', 'keywords'])
    const keys = fieldOrPath.split('.');
    let current = newConfig;
    for (let i = 0; i < keys.length - 1; i++) {
        if (!current[keys[i]]) current[keys[i]] = {}; // initialize if null
        current = current[keys[i]];
    }
    current[keys[keys.length - 1]] = value;

    onConfigChange(newConfig);
  };

  const mode = config.mode || 'crawl';
  const authRequired = !!config.credentials?.email;
  const source = config.source?.[0]?.name || 'twitter';
  const crawlInterval = config.crawl_interval || 60;
  
  const twitterParams = config.twitter_query?.params || {};
  const filters = twitterParams.filter || [];
  // For the input field, we join keywords to a comma-separated string
  const keywordsStr = (twitterParams.keywords || []).join(', ');
  
  const startDate = config.twitter_query?.start_date || '';
  const endDate = config.twitter_query?.end_date || '';

  // Helpers string from older config
  function getYesterdayDate() {
    const date = new Date();
    date.setDate(date.getDate() - 1);
    return date.toISOString().split('T')[0];
  }
  function getTodayDate() {
    return new Date().toISOString().split('T')[0];
  }

  return (
    <div className="p-6 bg-gray-900 text-gray-200 rounded-lg shadow-lg max-w-3xl mx-auto">
      <div className="flex items-center gap-4 mb-4">
        <label className="flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={mode === 'crawl'}
            onChange={(e) => {
              const newMode = e.target.checked ? 'crawl' : 'scrape';
              handleChange('mode', newMode);
              if (newMode === 'crawl') {
                  handleChange('twitter_query.start_date', getYesterdayDate());
                  handleChange('twitter_query.end_date', getTodayDate());
              }
            }}
            className="form-checkbox h-5 w-5 text-blue-500"
          />
          <span className="ml-2">Crawl Mode</span>
        </label>
      </div>

      {/* Crawl Interval */}
      <label className="block mb-4">
        {mode === 'crawl' ? 'Crawl Interval (seconds):' : 'Scraping Interval (seconds):'}
        <input
          type="number"
          value={crawlInterval}
          onChange={(e) => handleChange('crawl_interval', Number(e.target.value))}
          placeholder={mode === 'scrape' ? 'Scraping interval' : '60'}
          className="w-full p-2 mt-1 rounded-md bg-gray-800 border border-gray-700"
        />
      </label>

      {/* Source */}
      <label className="block mb-4">
        Source:
        <div className="flex gap-4 mt-1">
          <select
            value={source}
            onChange={(e) => {
                const selectedSource = AVAILABLE_SOURCES.find(s => s.id === e.target.value) || { id: e.target.value, baseUrl: '' };
                handleChange('source', [{ name: selectedSource.id, base_url: selectedSource.baseUrl }]);
            }}
            className="w-full p-2 py-1 rounded-md bg-gray-800 border border-gray-700"
          >
            {!AVAILABLE_SOURCES.find(s => s.id === source) && (
                <option value={source}>{source} (From API)</option>
            )}
            {AVAILABLE_SOURCES.map((src) => (
                <option key={src.id} value={src.id}>{src.label}</option>
            ))}
          </select>
        </div>
      </label>

      {/* Auth Required */}
      <label className="flex items-center cursor-pointer mb-4">
        <input
          type="checkbox"
          checked={authRequired}
          onChange={(e) => {
              if (e.target.checked) {
                  handleChange('credentials', { email: '', login: '', password: '' });
              } else {
                  handleChange('credentials', {});
              }
          }}
          className="form-checkbox h-5 w-5 text-blue-500"
        />
        <span className="ml-2">Auth Required</span>
      </label>

      {/* Credentials form only if authRequired = true */}
      {authRequired && (
        <div className="grid grid-cols-2 gap-4 mb-4">
          <input
            type="email"
            placeholder="Email"
            className="w-full p-2 rounded-md bg-gray-800 border border-gray-700"
            value={config.credentials?.email || ''}
            onChange={(e) => handleChange('credentials.email', e.target.value)}
          />
          <input
            type="text"
            placeholder="Username"
            className="w-full p-2 rounded-md bg-gray-800 border border-gray-700"
            value={config.credentials?.login || ''}
            onChange={(e) => handleChange('credentials.login', e.target.value)}
          />
          <input
            type="password"
            placeholder="Password"
            className="col-span-2 w-full p-2 rounded-md bg-gray-800 border border-gray-700"
            value={config.credentials?.password || ''}
            onChange={(e) => handleChange('credentials.password', e.target.value)}
          />
        </div>
      )}

      {/* Query Configuration */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold mb-2">Query</h3>

        {/* Filters */}
        <div>
          <span className="block mb-1">Filters:</span>
          {AVAILABLE_FILTERS.map((filter) => (
            <label key={filter.id} className="flex items-center gap-2 mb-1">
              <input
                type="checkbox"
                checked={filters.includes(filter.id)}
                onChange={(e) => {
                  const newFilters = e.target.checked
                    ? [...filters, filter.id]
                    : filters.filter((f) => f !== filter.id);
                  handleChange('twitter_query.params.filter', newFilters);
                }}
                className="form-checkbox h-4 w-4 text-blue-500"
              />
              <span className="ml-1">{filter.label}</span>
            </label>
          ))}
        </div>

        {/* Language */}
        <label className="block mb-4">
          Language:
          <input
            type="text"
            value={twitterParams.lang || 'en'}
            onChange={(e) => handleChange('twitter_query.params.lang', e.target.value)}
            className="w-full p-2 mt-1 rounded-md bg-gray-800 border border-gray-700"
          />
        </label>

        {/* Keywords */}
        <label className="block mb-4">
          Keywords (comma separated):
          <input
            type="text"
            value={keywordsStr}
            onChange={(e) => {
                const newKeywords = e.target.value.split(',').map((k) => k.trim()).filter(Boolean);
                handleChange('twitter_query.params.keywords', newKeywords);
            }}
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
              onChange={(e) => handleChange('twitter_query.start_date', e.target.value)}
              className="w-full p-2 mt-1 rounded-md bg-gray-800 border border-gray-700"
            />
          </label>
          <label className="flex-1">
            End date:
            <input
              type="date"
              value={endDate}
              onChange={(e) => handleChange('twitter_query.end_date', e.target.value)}
              className="w-full p-2 mt-1 rounded-md bg-gray-800 border border-gray-700"
            />
          </label>
        </div>
      </div>
    </div>
  );
}

