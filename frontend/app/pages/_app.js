import React from 'react';
import { UserConfigProvider } from '../utils/UserConfigContext'; // Zaimportuj swój Context Provider

function MyApp({ Component, pageProps }) {
    return (
        <UserConfigProvider>
            <Component {...pageProps} />
        </UserConfigProvider>
    );
}

export default MyApp;
