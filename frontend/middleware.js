import { NextResponse } from 'next/server';

const ACCESS_KEY_COOKIE = 'access_key';
const API_INTERNAL_URL = process.env.API_INTERNAL_URL;
const SESSION_SECRET = process.env.MIDDLEWARE_SESSION_SECRET;

function base64UrlEncode(buffer) {
    const binary = String.fromCharCode(...new Uint8Array(buffer));
    return btoa(binary)
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=+$/, '');
}

function base64UrlToBuffer(value) {
    const padded = value.replace(/-/g, '+').replace(/_/g, '/').padEnd(value.length + ((4 - (value.length % 4)) % 4), '=');
    const binary = atob(padded);
    return Uint8Array.from(binary, (c) => c.charCodeAt(0));
}

async function getHmacKey() {
    return crypto.subtle.importKey(
        'raw',
        new TextEncoder().encode(SESSION_SECRET),
        { name: 'HMAC', hash: 'SHA-256' },
        false,
        ['sign', 'verify']
    );
}

async function signKey(rawKey) {
    const hmacKey = await getHmacKey();
    const signature = await crypto.subtle.sign('HMAC', hmacKey, new TextEncoder().encode(rawKey));
    return `${rawKey}.${base64UrlEncode(signature)}`;
}

async function verifySignedCookie(cookieValue) {
    if (!cookieValue) return null;
    const separatorIndex = cookieValue.lastIndexOf('.');
    if (separatorIndex === -1) return null;

    const rawKey = cookieValue.slice(0, separatorIndex);
    const signaturePart = cookieValue.slice(separatorIndex + 1);

    try {
        const hmacKey = await getHmacKey();
        const isValid = await crypto.subtle.verify(
            'HMAC',
            hmacKey,
            base64UrlToBuffer(signaturePart),
            new TextEncoder().encode(rawKey)
        );
        return isValid ? rawKey : null;
    } catch {
        return null;
    }
}

async function verifyKeyAgainstBackend(rawKey) {
    if (!API_INTERNAL_URL) return false;
    try {
        const response = await fetch(`${API_INTERNAL_URL}/api/auth/verify-key/`, {
            headers: { 'X-Access-Key': rawKey },
        });
        return response.ok;
    } catch {
        return false;
    }
}

export async function middleware(request) {
    const { pathname, searchParams } = request.nextUrl;
    const keyParam = searchParams.get('key');

    if (keyParam) {
        const cleanUrl = request.nextUrl.clone();
        cleanUrl.searchParams.delete('key');

        const isValid = await verifyKeyAgainstBackend(keyParam);
        if (isValid) {
            cleanUrl.pathname = pathname === '/' ? '/views' : pathname;
            const response = NextResponse.redirect(cleanUrl);
            response.cookies.set(ACCESS_KEY_COOKIE, await signKey(keyParam), {
                path: '/',
                sameSite: 'lax',
                secure: process.env.NODE_ENV === 'production',
            });
            return response;
        }

        const response = NextResponse.redirect(cleanUrl);
        response.cookies.delete(ACCESS_KEY_COOKIE);
        return response;
    }

    const rawKey = await verifySignedCookie(request.cookies.get(ACCESS_KEY_COOKIE)?.value);

    if (rawKey) {
        if (pathname === '/') {
            return NextResponse.redirect(new URL('/views', request.url));
        }
        return NextResponse.next();
    }

    if (pathname.startsWith('/views')) {
        return NextResponse.redirect(new URL('/', request.url));
    }

    return NextResponse.next();
}

export const config = {
    matcher: ['/', '/views/:path*'],
};
