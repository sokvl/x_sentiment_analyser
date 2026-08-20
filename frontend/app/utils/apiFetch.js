const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

export default function apiFetch(path, options = {}) {
    return fetch(`${API_BASE_URL}${path}`, options);
}
