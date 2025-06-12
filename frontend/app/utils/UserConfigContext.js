'use client';
import React, { createContext, useReducer, useContext, useEffect } from 'react';

const UserConfigContext = createContext();

const userConfigReducer = (state, action) => {
    switch (action.type) {
        case 'SET_CONFIG':
            return { ...state, ...action.payload, isLoaded: true, loading: false };
        case 'CLEAR_CONFIG':
            return { config_name: '', tickers: [], isLoaded: false, loading: false };
        case 'SET_LOADING':
            return { ...state, loading: true };
        case 'SET_ERROR':
            return { ...state, error: action.payload, loading: false };
        default:
            return state;
    }
};

export const UserConfigProvider = ({ children }) => {
    const [state, dispatch] = useReducer(userConfigReducer, {
        config_name: '',
        tickers: [],
        isLoaded: false,
        loading: false,
        error: null,
    });

    const fetchActiveConfig = async () => {
        dispatch({ type: 'SET_LOADING' });
        try {
            const response = await fetch('http://localhost:8000/api/config/?active=true');
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            const data = await response.json();

            if (data.length > 0) {
                const activeConfig = data[0];
                const { name, config_string } = activeConfig;

                dispatch({
                    type: 'SET_CONFIG',
                    payload: {
                        config_name: name,
                        tickers: config_string?.user_config?.tickers || [],
                    },
                });
            } else {
                dispatch({ type: 'SET_ERROR', payload: 'No active configuration found' });
            }
        } catch (error) {
            dispatch({ type: 'SET_ERROR', payload: `Error fetching configuration: ${error.message}` });
            console.error('Error fetching active configuration:', error);
        }
    };

    const refreshConfig = () => {
        dispatch({ type: 'CLEAR_CONFIG' });
        fetchActiveConfig();
    };

    useEffect(() => {
        if (!state.isLoaded && !state.loading && !state.error) {
            fetchActiveConfig();
        }
    }, [state.isLoaded, state.loading]);

    return (
        <UserConfigContext.Provider value={{ state, refreshConfig }}>
            {children}
        </UserConfigContext.Provider>
    );
};

// Custom hook do użycia kontekstu
export const useUserConfig = () => {
    const context = useContext(UserConfigContext);
    if (!context) {
        throw new Error('useUserConfig must be used within a UserConfigProvider');
    }
    return context;
};
