'use client';
import React, { useState } from 'react';

export default function JsonToggle({ config }) {
  const [isJsonEnabled, setIsJsonEnabled] = useState(false);

  const handleToggle = () => {
    setIsJsonEnabled((prev) => !prev);
  };

  const configJson = isJsonEnabled && config ? JSON.stringify(config, null, 2) : '';

  return (
    <div className="p-4 bg-gray-800 rounded-lg shadow-lg mb-6">
      <h3 className="text-lg font-semibold mb-2">Export Config as JSON</h3>
      <label className="inline-flex items-center cursor-pointer">
        <input
          type="checkbox"
          checked={isJsonEnabled}
          onChange={handleToggle}
          className="form-checkbox h-5 w-5 text-blue-500"
        />
        <span className="ml-2 text-sm">Enable JSON Output</span>
      </label>

      {isJsonEnabled && (
        <textarea
          className="w-full mt-4 p-2 rounded-md bg-gray-900 border border-gray-700 text-gray-200"
          rows={10}
          readOnly
          value={configJson}
        />
      )}
    </div>
  );
}
