// Default Configuration Constants

export const AVAILABLE_MODELS = [
  { id: 'LSTMCNNv1', label: 'LSTM-CNN v1' },
  { id: 'FinBERT', label: 'FinBERT Sentiment' },
  { id: 'TweetBERT', label: 'TweetBERT Sentiment' },
];

export const AVAILABLE_SOURCES = [
  { id: 'twitter', label: 'Twitter (X)', baseUrl: 'https://x.com/search?q=' },
];

export const AVAILABLE_FILTERS = [
  { id: 'links', label: 'Links' },
  { id: 'replies', label: 'Replies' },
  { id: 'media', label: 'Media' },
];

export const DEFAULT_KEYWORDS = ['stock', 'market', 'investing'];

export const DEFAULT_CRAWL_INTERVAL = 60;

export const DEFAULT_CONFIG = {
  config_id: 4,
  name: 'Test Config',
  active: true,
  config_string: {
    user_config: {
      model: 'FinBERT',
      tickers: ['TSLA', 'NVDA', 'AAPL', 'MSFT', 'GOOG'],
    },
    scrapers_config: [
      {
        source: [
          {
            name: 'twitter',
            base_url: 'https://x.com/search?q=',
          },
        ],
        threads: 1,
        credentials: {},
        twitter_query: {
          params: {
            lang: 'en',
            filter: ['links'],
            keywords: DEFAULT_KEYWORDS,
          },
          start_date: new Date(Date.now() - 86400000).toISOString().split('T')[0], // Yesterday
          end_date: new Date().toISOString().split('T')[0], // Today
        },
        crawl_interval: DEFAULT_CRAWL_INTERVAL,
        max_time_running: null,
        mode: 'crawl',
      },
    ],
  },
};
