import React from 'react';
import PropTypes from 'prop-types';

/**
 * Tile - komponent bazowy z ciemnym motywem.
 */
export default function Tile({ children, className }) {
    return (
        <div className={`relative rounded-lg shadow-md p-4 bg-gray-800 text-gray-200 ${className}`}>
            {children}
        </div>
    );
}

Tile.propTypes = {
    children: PropTypes.node.isRequired,
    className: PropTypes.string,
};

Tile.defaultProps = {
    className: '',
};
