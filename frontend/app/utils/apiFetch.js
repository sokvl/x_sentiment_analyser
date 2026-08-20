const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;
const ACCESS_KEY_COOKIE = 'access_key';

function getAccessKey() {
    if (typeof document === 'undefined') return null;
    const match = document.cookie.match(new RegExp(`(?:^|; )${ACCESS_KEY_COOKIE}=([^;]*)`));
    return match ? decodeURIComponent(match[1]) : null;
}

export default function apiFetch(path, options = {}) {
    const accessKey = getAccessKey();
    const headers = { ...options.headers };
    if (accessKey) {
        headers['X-Access-Key'] = accessKey;
    }
    return fetch(`${API_BASE_URL}${path}`, { ...options, headers });
}
