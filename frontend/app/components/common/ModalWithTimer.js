import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';

export default function ModalWithTimer({ text, duration = 5000, onClose }) {
    const [remainingTime, setRemainingTime] = useState(duration);
    const [progress, setProgress] = useState(100);

    useEffect(() => {
        const interval = 100;
        const timer = setInterval(() => {
            setRemainingTime((prev) => Math.max(prev - interval, 0));
            setProgress((prev) => Math.max((prev - (100 / (duration / interval))), 0));
        }, interval);

        if (remainingTime === 0) {
            clearInterval(timer);
            if (onClose) onClose();
        }

        return () => clearInterval(timer);
    }, [remainingTime, duration, onClose]);

    return (
        <div className="fixed top-0 left-0 right-0 bg-gray-800 text-white shadow-md z-50 p-4 rounded-md max-w-2xl mx-auto mt-4">
            <div className="flex justify-between items-center">
                <span className="text-lg font-medium">{text}</span>
                <button
                    onClick={onClose}
                    className="text-gray-300 hover:text-white focus:outline-none"
                >
                    ✕
                </button>
            </div>
            <div className="h-2 bg-gray-700 rounded-md mt-2 overflow-hidden">
                <div
                    style={{ width: `${progress}%` }}
                    className="h-full bg-blue-500 transition-all duration-100"
                ></div>
            </div>
        </div>
    );
}

ModalWithTimer.propTypes = {
    text: PropTypes.string.isRequired, // Tekst do wyświetlenia w modalu
    duration: PropTypes.number, // Czas trwania w ms (domyślnie 5000 ms)
    onClose: PropTypes.func.isRequired, // Funkcja zamykająca modal
};
