import { NextResponse } from 'next/server';

const ACCESS_KEY_COOKIE = 'access_key';

export function middleware(request) {
    const { searchParams } = request.nextUrl;
    const keyParam = searchParams.get('key');

    if (keyParam) {
        const cleanUrl = request.nextUrl.clone();
        cleanUrl.searchParams.delete('key');

        const response = NextResponse.redirect(cleanUrl);
        response.cookies.set(ACCESS_KEY_COOKIE, keyParam, {
            path: '/',
            sameSite: 'lax',
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
        });
        return response;
    }

    if (!request.cookies.has(ACCESS_KEY_COOKIE)) {
        return NextResponse.redirect(new URL('/', request.url));
    }

    return NextResponse.next();
}

export const config = {
    matcher: ['/views/:path*'],
};
